import numpy as np
from src.config import (
    DELTA_T, STEPS_PER_DAY, E_MIN, E_MAX, P_DIS_MAX, P_CHG_MAX,
    ETA_DIS, ETA_CHG, E_INIT, PENALTY_EMERGENCY, PENALTY_ADD,
    PENALTY_REDUCE, get_baseline_load_forecast
)
from src.data_loader import get_pv_forecast_10min

def run_q3_simulation(tariffs_matrix, load_actual_all, pv_actual_all,
                      pv_forecast_3d, start_day=31, num_days=334):
    """
    Executes the Q2 rolling framework plus intra-day plan adjustments
    using updated PV forecasts (Annex 3) issued at 0:00, 6:00, 12:00, 18:00.

    Adjustment settlement per step:
      * additions (plan raised):   1.5 * c(t)  (PENALTY_ADD)
      * reductions (plan lowered): 0.5 * c(t)  (PENALTY_REDUCE)
    """
    e_current = E_INIT
    total_cost_all = 0.0

    p_plan_all_kwh = []
    p_adj_all_kwh = []
    p_em_all_kwh = []
    e_bat_all_kwh = []

    for d in range(num_days):
        day_idx = start_day + d
        t_start = day_idx * STEPS_PER_DAY
        t_end = t_start + STEPS_PER_DAY

        tariff_d = tariffs_matrix[day_idx] if tariffs_matrix.ndim == 2 else tariffs_matrix
        load_act_d = load_actual_all[t_start:t_end]
        pv_act_d = pv_actual_all[t_start:t_end]

        load_pred_d = get_baseline_load_forecast(load_actual_all[:t_start])

        # 1. Day-ahead plan at 0:00 using the 0:00 Annex 3 PV forecast.
        pv_fc_0 = get_pv_forecast_10min(pv_forecast_3d, day_idx, 0)
        p_plan_orig = np.maximum(0.0, load_pred_d * 1.05 - pv_fc_0)
        p_plan = p_plan_orig.copy()
        adj_cost = 0.0

        # 2. Intra-day adjustments at 6:00, 12:00, 18:00.
        for issue_hour in (6, 12, 18):
            pv_fc_tau = get_pv_forecast_10min(pv_forecast_3d, day_idx, issue_hour)
            mask = ~np.isnan(pv_fc_tau)
            p_need = np.maximum(0.0, load_pred_d * 1.05 - pv_fc_tau)
            delta = p_need - p_plan
            p_plan[mask] = p_need[mask]

            additions = np.where(mask, np.maximum(0.0, delta), 0.0)
            reductions = np.where(mask, np.maximum(0.0, -delta), 0.0)
            adj_cost += np.sum(
                (PENALTY_ADD * tariff_d * additions
                 + PENALTY_REDUCE * tariff_d * reductions) * DELTA_T
            )

        # 3. Real-time dispatch (battery + emergency purchase) on final plan.
        p_em_day = np.zeros(STEPS_PER_DAY)
        e_bat_day = np.zeros(STEPS_PER_DAY)

        for t in range(STEPS_PER_DAY):
            deficit_kw = max(0.0, load_act_d[t] - (p_plan[t] + pv_act_d[t]))
            surplus_kw = max(0.0, (p_plan[t] + pv_act_d[t]) - load_act_d[t])

            p_dis = 0.0
            p_chg = 0.0

            if deficit_kw > 0:
                max_dis_from_soc = (e_current - E_MIN) * ETA_DIS / DELTA_T
                p_dis = min(deficit_kw, P_DIS_MAX, max_dis_from_soc)
                p_dis = max(0.0, p_dis)
                p_em_day[t] = deficit_kw - p_dis
            elif surplus_kw > 0:
                max_chg_from_soc = (E_MAX - e_current) / (ETA_CHG * DELTA_T)
                p_chg = min(surplus_kw, P_CHG_MAX, max_chg_from_soc)
                p_chg = max(0.0, p_chg)

            e_current = e_current + (p_chg * ETA_CHG - p_dis / ETA_DIS) * DELTA_T
            e_bat_day[t] = e_current

        # 4. Daily cost: day-ahead contract + adjustment settlement + emergency.
        daily_cost = (np.sum(tariff_d * p_plan_orig * DELTA_T)
                      + adj_cost
                      + np.sum(PENALTY_EMERGENCY * tariff_d * p_em_day * DELTA_T))
        total_cost_all += daily_cost

        p_plan_all_kwh.extend(p_plan * DELTA_T)
        p_adj_all_kwh.extend((p_plan - p_plan_orig) * DELTA_T)
        p_em_all_kwh.extend(p_em_day * DELTA_T)
        e_bat_all_kwh.extend(e_bat_day)

    return {
        "p_plan_kwh": np.array(p_plan_all_kwh),
        "p_adj_kwh": np.array(p_adj_all_kwh),
        "p_em_kwh": np.array(p_em_all_kwh),
        "e_bat_kwh": np.array(e_bat_all_kwh),
        "total_cost": total_cost_all
    }