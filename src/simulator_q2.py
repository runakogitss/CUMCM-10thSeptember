import numpy as np
from src.config import (
    DELTA_T, STEPS_PER_DAY, E_MIN, E_MAX, P_DIS_MAX, P_CHG_MAX,
    ETA_DIS, ETA_CHG, E_INIT, PENALTY_EMERGENCY, SAFETY_BUFFER_ALPHA,
    SIM_START_DAY, SIM_NUM_DAYS,
    get_baseline_load_forecast, get_baseline_pv_forecast
)


def run_q2_simulation(tariffs_matrix, load_actual_all, pv_actual_all,
                      start_day=SIM_START_DAY, num_days=SIM_NUM_DAYS):
    """
    Question 2: 0:00 day-ahead commitment plus real-time battery-first dispatch.

    For every day d in the simulation range a 144-step plan is fixed at 0:00
    from load/PV forecasts built only on historical (prior) data. During the
    day the battery absorbs surpluses and covers deficits first; any residual
    deficit is settled as a penalised emergency purchase.
    """
    e_current = float(E_INIT)
    total_cost_all = 0.0
    total_planned_cost = 0.0
    total_emergency_cost = 0.0

    p_plan_all_kwh = []
    p_em_all_kwh = []
    p_chg_all_kwh = []
    p_dis_all_kwh = []
    e_bat_all_kwh = []

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

        load_pred_d = get_baseline_load_forecast(load_actual_all[:t_start])
        pv_pred_d = get_baseline_pv_forecast(pv_actual_all[:t_start])
        net_load_pred = load_pred_d - pv_pred_d
        p_plan_kw = np.maximum(0.0, net_load_pred * SAFETY_BUFFER_ALPHA)

        p_em_day = np.zeros(STEPS_PER_DAY)
        p_chg_day = np.zeros(STEPS_PER_DAY)
        p_dis_day = np.zeros(STEPS_PER_DAY)
        e_bat_day = np.zeros(STEPS_PER_DAY)

        e_day_start[d] = e_current

        for t in range(STEPS_PER_DAY):
            deficit_kw = max(0.0, load_act_d[t] - (p_plan_kw[t] + pv_act_d[t]))
            surplus_kw = max(0.0, (p_plan_kw[t] + pv_act_d[t]) - load_act_d[t])

            p_dis = 0.0
            p_chg = 0.0

            if deficit_kw > 0.0:
                max_dis_from_soc = max(0.0, (e_current - E_MIN) * ETA_DIS / DELTA_T)
                p_dis = min(deficit_kw, P_DIS_MAX, max_dis_from_soc)
                p_em_day[t] = deficit_kw - p_dis
            elif surplus_kw > 0.0:
                max_chg_from_soc = max(0.0, (E_MAX - e_current) / (ETA_CHG * DELTA_T))
                p_chg = min(surplus_kw, P_CHG_MAX, max_chg_from_soc)

            e_current = e_current + (p_chg * ETA_CHG - p_dis / ETA_DIS) * DELTA_T
            e_current = float(min(E_MAX, max(E_MIN, e_current)))

            p_chg_day[t] = p_chg
            p_dis_day[t] = p_dis
            e_bat_day[t] = e_current

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

    p_plan_all_kwh = np.asarray(p_plan_all_kwh)
    p_em_all_kwh = np.asarray(p_em_all_kwh)

    return {
        "p_plan_kwh": p_plan_all_kwh,
        "p_em_kwh": p_em_all_kwh,
        "p_chg_kwh": np.asarray(p_chg_all_kwh),
        "p_dis_kwh": np.asarray(p_dis_all_kwh),
        "e_bat_kwh": np.asarray(e_bat_all_kwh),
        "e_day_start": e_day_start,
        "daily_plan_energy": daily_plan_energy,
        "daily_planned_cost": daily_planned_cost,
        "daily_emergency_cost": daily_emergency_cost,
        "total_plan_kwh": float(np.sum(p_plan_all_kwh)),
        "total_em_kwh": float(np.sum(p_em_all_kwh)),
        "total_planned_cost": total_planned_cost,
        "total_emergency_cost": total_emergency_cost,
        "total_cost": total_cost_all,
        "start_day": start_day,
        "num_days": num_days,
    }
