import numpy as np
import scipy.optimize as opt

from src.config import (
    DELTA_T, STEPS_PER_DAY, E_MIN, E_MAX, P_CHG_MAX, P_DIS_MAX,
    ETA_CHG, ETA_DIS, E_INIT, PENALTY_ADD, PENALTY_REDUCE, PENALTY_EMERGENCY,
    SAFETY_BUFFER_ALPHA, SIM_START_DAY, SIM_NUM_DAYS,
    get_baseline_load_forecast, get_baseline_pv_forecast,
)
from src.data_loader import get_pv_forecast_10min

# Intra-day rolling epochs (10-min step index): 0:00, 6:00, 12:00, 18:00.
ROLLING_EPOCHS = (0, 36, 72, 108)
ISSUE_HOUR_BY_EPOCH = {0: 0, 36: 6, 72: 12, 108: 18}

# Variable layout per horizon step t:
#   0: P_adj, 1: dP+, 2: dP-, 3: P_chg, 4: P_dis, 5: P_em, 6: P_curt, 7: E_bat
VARS_PER_STEP = 8


def solve_epoch_lp(p_plan_h, pv_fc_h, load_fc_h, tariff_h, soc_start):
    """
    Solves the intra-day MPC linear program over a rolling horizon.

    Decision variables are in kW (E_bat in kWh). Minimizes the adjustment
    surcharge/breach fees plus the emergency penalty while respecting the
    power balance and battery energy constraints.

    Returns the adjusted purchase plan P_adj (kW) for the horizon.
    """
    n = len(p_plan_h)
    nvars = VARS_PER_STEP * n

    def idx(t, v):
        return t * VARS_PER_STEP + v

    c = np.zeros(nvars)
    for t in range(n):
        c[idx(t, 1)] = PENALTY_ADD * tariff_h[t] * DELTA_T
        c[idx(t, 2)] = PENALTY_REDUCE * tariff_h[t] * DELTA_T
        c[idx(t, 5)] = PENALTY_EMERGENCY * tariff_h[t] * DELTA_T

    bounds = []
    for t in range(n):
        bounds.append((0.0, None))              # P_adj
        bounds.append((0.0, None))              # dP+
        bounds.append((0.0, None))              # dP-
        bounds.append((0.0, P_CHG_MAX))         # P_chg
        bounds.append((0.0, P_DIS_MAX))         # P_dis
        bounds.append((0.0, None))              # P_em
        bounds.append((0.0, None))              # P_curt
        bounds.append((E_MIN, E_MAX))           # E_bat

    A_eq, b_eq = [], []
    for t in range(n):
        # P_adj(t) - P_plan(t) = dP+(t) - dP-(t)
        row = np.zeros(nvars)
        row[idx(t, 0)] = 1.0
        row[idx(t, 1)] = -1.0
        row[idx(t, 2)] = 1.0
        A_eq.append(row)
        b_eq.append(float(p_plan_h[t]))

        # P_adj + P_pv + P_dis + P_em - P_chg - P_curt = P_load
        row = np.zeros(nvars)
        row[idx(t, 0)] = 1.0
        row[idx(t, 3)] = -1.0
        row[idx(t, 4)] = 1.0
        row[idx(t, 5)] = 1.0
        row[idx(t, 6)] = -1.0
        A_eq.append(row)
        b_eq.append(float(load_fc_h[t] - pv_fc_h[t]))

        # E(t) - E(t-1) = (eta_chg*P_chg - P_dis/eta_dis) * dt
        row = np.zeros(nvars)
        row[idx(t, 7)] = 1.0
        row[idx(t, 3)] = -ETA_CHG * DELTA_T
        row[idx(t, 4)] = DELTA_T / ETA_DIS
        if t > 0:
            row[idx(t - 1, 7)] = -1.0
        A_eq.append(row)
        b_eq.append(float(soc_start if t == 0 else 0.0))

    res = opt.linprog(c, A_eq=np.array(A_eq), b_eq=np.array(b_eq),
                      bounds=bounds, method="highs")
    if not res.success:
        raise RuntimeError(f"Q3 epoch LP failed: {res.message}")

    return np.array([res.x[idx(t, 0)] for t in range(n)])


def run_q3_simulation(tariffs_matrix, load_actual_all, pv_actual_all,
                      pv_forecast_3d, start_day=SIM_START_DAY, num_days=SIM_NUM_DAYS):
    """
    Question 3 rolling-horizon MPC from Feb 1 to Dec 31 2025.

    A baseline plan P_plan is committed at 0:00 from the rolling net-load
    forecast (the same day-ahead baseline as Question 2). At each rolling
    epoch (0:00/6:00/12:00/18:00) the newly arrived Annex 3 PV forecast and
    the current battery state are used to re-optimise the remaining purchase
    schedule P_adj. Real-time battery-first dispatch then settles against the
    actual load/PV, with emergency purchases covering residual deficits.
    """
    e_current = float(E_INIT)
    total_cost_all = 0.0
    total_planned_cost = 0.0
    total_adjust_cost = 0.0
    total_emergency_cost = 0.0

    p_plan_all_kwh = []
    p_adj_all_kwh = []
    p_em_all_kwh = []
    p_chg_all_kwh = []
    p_dis_all_kwh = []
    e_bat_all_kwh = []

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

        p_adj_final = p_plan_kw.copy()
        p_em_day = np.zeros(STEPS_PER_DAY)
        p_chg_day = np.zeros(STEPS_PER_DAY)
        p_dis_day = np.zeros(STEPS_PER_DAY)
        e_bat_day = np.zeros(STEPS_PER_DAY)

        for t in range(STEPS_PER_DAY):
            if t in ROLLING_EPOCHS:
                pv_fc_h = get_pv_forecast_10min(
                    pv_forecast_3d, day_idx, ISSUE_HOUR_BY_EPOCH[t]
                )
                pv_fc_h = np.where(np.isnan(pv_fc_h), 0.0, pv_fc_h)
                p_adj_new = solve_epoch_lp(
                    p_plan_kw[t:], pv_fc_h[t:], load_pred_d[t:],
                    tariff_d[t:], e_current,
                )
                p_adj_final[t:] = p_adj_new

            deficit_kw = max(0.0, load_act_d[t] - (p_adj_final[t] + pv_act_d[t]))
            surplus_kw = max(0.0, (p_adj_final[t] + pv_act_d[t]) - load_act_d[t])

            p_dis = 0.0
            p_chg = 0.0
            if deficit_kw > 0.0:
                max_dis_from_soc = max(0.0, (e_current - E_MIN) * ETA_DIS / DELTA_T)
                p_dis = min(deficit_kw, P_DIS_MAX, max_dis_from_soc)
                p_em_day[t] = deficit_kw - p_dis
            elif surplus_kw > 0.0:
                max_chg_from_soc = max(0.0, (E_MAX - e_current) / (ETA_CHG * DELTA_T))
                p_chg = min(surplus_kw, P_CHG_MAX, max_chg_from_soc)

            e_current = float(min(E_MAX, max(E_MIN,
                             e_current + (p_chg * ETA_CHG - p_dis / ETA_DIS) * DELTA_T)))
            p_chg_day[t] = p_chg
            p_dis_day[t] = p_dis
            e_bat_day[t] = e_current

        dpp = np.maximum(0.0, p_adj_final - p_plan_kw)
        dpm = np.maximum(0.0, p_plan_kw - p_adj_final)

        planned_cost_day = float(np.sum(tariff_d * p_plan_kw * DELTA_T))
        adjust_cost_day = float(
            np.sum((PENALTY_ADD * tariff_d * dpp
                    + PENALTY_REDUCE * tariff_d * dpm) * DELTA_T)
        )
        emergency_cost_day = float(
            np.sum(PENALTY_EMERGENCY * tariff_d * p_em_day * DELTA_T)
        )

        total_planned_cost += planned_cost_day
        total_adjust_cost += adjust_cost_day
        total_emergency_cost += emergency_cost_day
        total_cost_all += planned_cost_day + adjust_cost_day + emergency_cost_day

        p_plan_all_kwh.extend(p_plan_kw * DELTA_T)
        p_adj_all_kwh.extend(p_adj_final * DELTA_T)
        p_em_all_kwh.extend(p_em_day * DELTA_T)
        p_chg_all_kwh.extend(p_chg_day * DELTA_T)
        p_dis_all_kwh.extend(p_dis_day * DELTA_T)
        e_bat_all_kwh.extend(e_bat_day)

    p_plan_all_kwh = np.asarray(p_plan_all_kwh)
    p_adj_all_kwh = np.asarray(p_adj_all_kwh)
    p_em_all_kwh = np.asarray(p_em_all_kwh)

    return {
        "p_plan_kwh": p_plan_all_kwh,
        "p_adj_kwh": p_adj_all_kwh,
        "p_em_kwh": p_em_all_kwh,
        "p_chg_kwh": np.asarray(p_chg_all_kwh),
        "p_dis_kwh": np.asarray(p_dis_all_kwh),
        "e_bat_kwh": np.asarray(e_bat_all_kwh),
        "total_plan_kwh": float(np.sum(p_plan_all_kwh)),
        "total_adj_kwh": float(np.sum(p_adj_all_kwh)),
        "total_em_kwh": float(np.sum(p_em_all_kwh)),
        "total_planned_cost": total_planned_cost,
        "total_adjust_cost": total_adjust_cost,
        "total_emergency_cost": total_emergency_cost,
        "total_cost": total_cost_all,
        "start_day": start_day,
        "num_days": num_days,
    }