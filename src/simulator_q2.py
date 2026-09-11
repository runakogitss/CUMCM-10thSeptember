import numpy as np
import scipy.optimize as opt

from src.config import (
    DELTA_T, STEPS_PER_DAY, E_MIN, E_MAX, P_DIS_MAX, P_CHG_MAX,
    ETA_DIS, ETA_CHG, E_INIT, PENALTY_EMERGENCY, SAFETY_BUFFER_ALPHA,
    FORECAST_WINDOW_DAYS, ROBUST_Z, E_PLAN_MIN, E_TERMINAL_TARGET, WARMUP_DAYS,
    SIM_START_DAY, SIM_NUM_DAYS,
    get_baseline_load_forecast, get_baseline_pv_forecast,
)

# Stage-1 LP variable layout per step t: 0:P_plan, 1:P_chg, 2:P_dis, 3:E_bat
STAGE1_VARS_PER_STEP = 4


def get_robust_net_load(historical_load, historical_pv, window_days=FORECAST_WINDOW_DAYS,
                        z=ROBUST_Z):
    """
    Stage-1 robust net-load estimator.

    Computes the per-slot mean and standard deviation of load and PV over the
    last `window_days`, combines them into a net-load standard deviation, and
    hedges with the `z`-quantile buffer (0.842 ~ 80th percentile) against the
    5x emergency penalty.
    """
    hist_load = np.asarray(historical_load, dtype=float)
    hist_pv = np.asarray(historical_pv, dtype=float)
    available_days = len(hist_load) // STEPS_PER_DAY
    window_days = int(min(window_days, available_days))
    if window_days < 1:
        return np.zeros(STEPS_PER_DAY)

    tail = window_days * STEPS_PER_DAY
    load_mat = hist_load[-tail:].reshape((window_days, STEPS_PER_DAY))
    pv_mat = hist_pv[-tail:].reshape((window_days, STEPS_PER_DAY))

    mu_load = load_mat.mean(axis=0)
    mu_pv = pv_mat.mean(axis=0)
    ddof = 1 if window_days > 1 else 0
    sig_load = load_mat.std(axis=0, ddof=ddof)
    sig_pv = pv_mat.std(axis=0, ddof=ddof)
    sig_net = np.sqrt(sig_load ** 2 + sig_pv ** 2)

    robust = mu_load - mu_pv + z * sig_net
    return np.maximum(0.0, robust)


def solve_stage1_lp(net_robust, tariff, e_start,
                    e_plan_min=E_PLAN_MIN, e_terminal=E_TERMINAL_TARGET):
    """
    Stage-1 deterministic day-ahead LP (144 steps).

    Determines the arbitrage-optimised purchase schedule P_plan(t) that
    minimises the day-ahead purchase cost subject to the robust net-load
    balance, battery dynamics and inter-day terminal SOC target.
    """
    n = STEPS_PER_DAY
    nvars = STAGE1_VARS_PER_STEP * n

    def idx(t, v):
        return t * STAGE1_VARS_PER_STEP + v

    c = np.zeros(nvars)
    for t in range(n):
        c[idx(t, 0)] = float(tariff[t]) * DELTA_T

    bounds = []
    for t in range(n):
        bounds.append((0.0, None))            # P_plan
        bounds.append((0.0, P_CHG_MAX))       # P_chg
        bounds.append((0.0, P_DIS_MAX))       # P_dis
        if t == 0:
            bounds.append((min(e_plan_min, float(e_start)), E_MAX))
        else:
            bounds.append((e_plan_min, E_MAX))

    A_eq, b_eq = [], []
    for t in range(n):
        # P_plan + P_dis - P_chg = P_net_robust
        row = np.zeros(nvars)
        row[idx(t, 0)] = 1.0
        row[idx(t, 2)] = 1.0
        row[idx(t, 1)] = -1.0
        A_eq.append(row)
        b_eq.append(float(net_robust[t]))

        # E(t) - E(t-1) = (eta_chg*P_chg - P_dis/eta_dis) * dt
        row = np.zeros(nvars)
        row[idx(t, 3)] = 1.0
        row[idx(t, 1)] = -ETA_CHG * DELTA_T
        row[idx(t, 2)] = DELTA_T / ETA_DIS
        if t > 0:
            row[idx(t - 1, 3)] = -1.0
        A_eq.append(row)
        b_eq.append(float(e_start if t == 0 else 0.0))

    # Terminal inter-day constraint: E(24:00) >= E_TERMINAL_TARGET
    A_ub = []
    b_ub = []
    row = np.zeros(nvars)
    row[idx(n - 1, 3)] = -1.0
    A_ub.append(row)
    b_ub.append(-float(e_terminal))

    res = opt.linprog(c, A_eq=np.array(A_eq), b_eq=np.array(b_eq),
                      A_ub=np.array(A_ub), b_ub=np.array(b_ub),
                      bounds=bounds, method="highs")
    if not res.success:
        raise RuntimeError(f"Q2 Stage-1 LP failed: {res.message}")

    return np.array([res.x[idx(t, 0)] for t in range(n)])


def _real_time_dispatch(p_plan_d, load_act_d, pv_act_d, e_start):
    """
    Stage-2 real-time battery-first dispatch for one day.

    Battery covers deficits first (up to power/SOC limits), emergency covers
    the rest; surpluses charge the battery. Returns per-step arrays and the
    terminal battery energy.
    """
    e_current = float(e_start)
    p_em = np.zeros(STEPS_PER_DAY)
    p_chg = np.zeros(STEPS_PER_DAY)
    p_dis = np.zeros(STEPS_PER_DAY)
    e_bat = np.zeros(STEPS_PER_DAY)

    for t in range(STEPS_PER_DAY):
        deficit_kw = max(0.0, load_act_d[t] - (p_plan_d[t] + pv_act_d[t]))
        surplus_kw = max(0.0, (p_plan_d[t] + pv_act_d[t]) - load_act_d[t])

        p_dis_kw = 0.0
        p_chg_kw = 0.0
        if deficit_kw > 0.0:
            max_dis_from_soc = max(0.0, (e_current - E_MIN) * ETA_DIS / DELTA_T)
            p_dis_kw = min(deficit_kw, P_DIS_MAX, max_dis_from_soc)
            p_em[t] = deficit_kw - p_dis_kw
        elif surplus_kw > 0.0:
            max_chg_from_soc = max(0.0, (E_MAX - e_current) / (ETA_CHG * DELTA_T))
            p_chg_kw = min(surplus_kw, P_CHG_MAX, max_chg_from_soc)

        e_current = float(min(E_MAX, max(E_MIN,
                         e_current + (p_chg_kw * ETA_CHG - p_dis_kw / ETA_DIS) * DELTA_T)))
        p_chg[t] = p_chg_kw
        p_dis[t] = p_dis_kw
        e_bat[t] = e_current

    return p_em, p_chg, p_dis, e_bat, e_current


def run_q2_simulation(tariffs_matrix, load_actual_all, pv_actual_all,
                      start_day=SIM_START_DAY, num_days=SIM_NUM_DAYS):
    """
    Question 2 two-stage robust & arbitrage-optimised rolling framework.

    Stage 0 (warm-up): January 1-31 is simulated with the same two-stage logic
    so the battery SOC evolves naturally and seeds Feb 1 with the exact
    January 31 terminal state.
    Stage 1: a 144-step LP at 0:00 derives the day-ahead plan P_plan from the
    80th-percentile robust net-load estimate with valley/peak arbitrage.
    Stage 2: real-time battery-first dispatch against actual load/PV.
    """
    if start_day < WARMUP_DAYS:
        raise ValueError("start_day must be >= WARMUP_DAYS (31) so January is used as prior")

    e_current = float(E_INIT)

    for d in range(start_day):
        t_start = d * STEPS_PER_DAY
        tariff_d = tariffs_matrix[d] if tariffs_matrix.ndim == 2 else tariffs_matrix
        net_robust = get_robust_net_load(load_actual_all[:t_start], pv_actual_all[:t_start])
        p_plan_d = solve_stage1_lp(net_robust, tariff_d, e_current)
        _, _, _, _, e_current = _real_time_dispatch(
            p_plan_d,
            load_actual_all[t_start:t_start + STEPS_PER_DAY],
            pv_actual_all[t_start:t_start + STEPS_PER_DAY],
            e_current,
        )

    total_cost_all = 0.0
    total_planned_cost = 0.0
    total_emergency_cost = 0.0

    p_plan_all_kwh = []
    p_em_all_kwh = []
    p_chg_all_kwh = []
    p_dis_all_kwh = []
    e_bat_all_kwh = []
    p_em_cost_all = []

    e_day_start = np.zeros(num_days)
    daily_plan_energy = np.zeros(num_days)
    daily_planned_cost = np.zeros(num_days)
    daily_emergency_cost = np.zeros(num_days)

    for d in range(num_days):
        day_idx = start_day + d
        t_start = day_idx * STEPS_PER_DAY
        t_end = t_start + STEPS_PER_DAY

        tariff_d = tariffs_matrix[day_idx] if tariffs_matrix.ndim == 2 else tariffs_matrix
        load_act_d = np.asarray(load_actual_all[t_start:t_end], dtype=float)
        pv_act_d = np.asarray(pv_actual_all[t_start:t_end], dtype=float)

        net_robust = get_robust_net_load(load_actual_all[:t_start], pv_actual_all[:t_start])
        p_plan_kw = solve_stage1_lp(net_robust, tariff_d, e_current)

        e_day_start[d] = e_current
        p_em_day, p_chg_day, p_dis_day, e_bat_day, e_current = _real_time_dispatch(
            p_plan_kw, load_act_d, pv_act_d, e_current,
        )

        planned_cost_day = float(np.sum(tariff_d * p_plan_kw * DELTA_T))
        emergency_cost_day = float(
            np.sum(PENALTY_EMERGENCY * tariff_d * p_em_day * DELTA_T)
        )
        daily_plan_energy[d] = float(np.sum(p_plan_kw * DELTA_T))
        daily_planned_cost[d] = planned_cost_day
        daily_emergency_cost[d] = emergency_cost_day

        total_planned_cost += planned_cost_day
        total_emergency_cost += emergency_cost_day
        total_cost_all += planned_cost_day + emergency_cost_day

        p_plan_all_kwh.extend(p_plan_kw * DELTA_T)
        p_em_all_kwh.extend(p_em_day * DELTA_T)
        p_chg_all_kwh.extend(p_chg_day * DELTA_T)
        p_dis_all_kwh.extend(p_dis_day * DELTA_T)
        e_bat_all_kwh.extend(e_bat_day)
        p_em_cost_all.extend(PENALTY_EMERGENCY * tariff_d * p_em_day * DELTA_T)

    p_plan_all_kwh = np.asarray(p_plan_all_kwh)
    p_em_all_kwh = np.asarray(p_em_all_kwh)

    return {
        "p_plan_kwh": p_plan_all_kwh,
        "p_em_kwh": p_em_all_kwh,
        "p_chg_kwh": np.asarray(p_chg_all_kwh),
        "p_dis_kwh": np.asarray(p_dis_all_kwh),
        "e_bat_kwh": np.asarray(e_bat_all_kwh),
        "p_em_cost": np.asarray(p_em_cost_all),
        "e_day_start": e_day_start,
        "daily_plan_energy": daily_plan_energy,
        "daily_planned_cost": daily_planned_cost,
        "daily_emergency_cost": daily_emergency_cost,
        "total_plan_kwh": float(np.sum(p_plan_all_kwh)),
        "total_em_kwh": float(np.sum(p_em_all_kwh)),
        "total_planned_cost": total_planned_cost,
        "total_emergency_cost": total_emergency_cost,
        "total_cost": total_cost_all,
        "warmup_end_soc": e_current,
        "start_day": start_day,
        "num_days": num_days,
    }


def run_q2_baseline_simulation(tariffs_matrix, load_actual_all, pv_actual_all,
                               start_day=SIM_START_DAY, num_days=SIM_NUM_DAYS):
    """
    Legacy Question 2 heuristic baseline (passive battery buffer with a static
    SAFETY_BUFFER_ALPHA and no arbitrage), kept for cost comparison.
    """
    e_current = E_INIT
    total_cost_all = 0.0

    for d in range(num_days):
        day_idx = start_day + d
        t_start = day_idx * STEPS_PER_DAY
        t_end = t_start + STEPS_PER_DAY

        tariff_d = tariffs_matrix[day_idx] if tariffs_matrix.ndim == 2 else tariffs_matrix
        load_act_d = np.asarray(load_actual_all[t_start:t_end], dtype=float)
        pv_act_d = np.asarray(pv_actual_all[t_start:t_end], dtype=float)

        load_pred_d = get_baseline_load_forecast(load_actual_all[:t_start])
        pv_pred_d = get_baseline_pv_forecast(pv_actual_all[:t_start])
        p_plan_kw = np.maximum(0.0, (load_pred_d - pv_pred_d) * SAFETY_BUFFER_ALPHA)

        p_em_day, _, _, _, e_current = _real_time_dispatch(
            p_plan_kw, load_act_d, pv_act_d, e_current,
        )
        daily_cost = float(
            np.sum((tariff_d * p_plan_kw + PENALTY_EMERGENCY * tariff_d * p_em_day) * DELTA_T)
        )
        total_cost_all += daily_cost

    return {"total_cost": total_cost_all, "start_day": start_day, "num_days": num_days}