import numpy as np
from src.config import (
    DELTA_T, STEPS_PER_DAY, E_MIN, E_MAX, P_DIS_MAX, P_CHG_MAX, 
    ETA_DIS, ETA_CHG, E_INIT, PENALTY_EMERGENCY, get_baseline_load_forecast
)

def run_q2_simulation(tariffs_matrix, load_actual_all, pv_actual_all, start_day=31, num_days=334):
    """
    Executes day-ahead rolling planning from Feb 1 (Day 31) to Dec 31[cite: 2].
    """
    e_current = E_INIT
    total_cost_all = 0.0
    
    p_plan_all_kwh = []
    p_em_all_kwh = []
    e_bat_all_kwh = []

    for d in range(num_days):
        day_idx = start_day + d
        t_start = day_idx * STEPS_PER_DAY
        t_end = t_start + STEPS_PER_DAY
        
        # Current Day Tariffs & Actuals
        tariff_d = tariffs_matrix[day_idx] if tariffs_matrix.ndim == 2 else tariffs_matrix
        load_act_d = load_actual_all[t_start:t_end]
        pv_act_d = pv_actual_all[t_start:t_end]
        
        # 1. Day-Ahead Planning at 0:00 using historical baseline load & forecast PV[cite: 2]
        load_pred_d = get_baseline_load_forecast(load_actual_all[:t_start])
        # Add safety margin to plan against 5x penalty[cite: 2]
        p_plan_kw = np.maximum(0.0, load_pred_d * 1.05 - pv_act_d)
        
        # 2. Real-Time Dispatch Loop (10-min steps)
        p_em_day = np.zeros(STEPS_PER_DAY)
        e_bat_day = np.zeros(STEPS_PER_DAY)
        
        for t in range(STEPS_PER_DAY):
            # Deficit(t) = max(0, P_load_act(t) - (P_plan(t) + P_pv_act(t)))
            deficit_kw = max(0.0, load_act_d[t] - (p_plan_kw[t] + pv_act_d[t]))
            surplus_kw = max(0.0, (p_plan_kw[t] + pv_act_d[t]) - load_act_d[t])
            
            p_dis = 0.0
            p_chg = 0.0
            
            if deficit_kw > 0:
                # Discharge battery first up to P_dis_max and E_min
                max_dis_from_soc = (e_current - E_MIN) * ETA_DIS / DELTA_T
                p_dis = min(deficit_kw, P_DIS_MAX, max_dis_from_soc)
                p_dis = max(0.0, p_dis)
                
                # Unfulfilled deficit becomes emergency purchase P_em
                unfilled_kw = deficit_kw - p_dis
                p_em_day[t] = unfilled_kw
            elif surplus_kw > 0:
                # Charge battery up to P_chg_max and E_max
                max_chg_from_soc = (E_MAX - e_current) / (ETA_CHG * DELTA_T)
                p_chg = min(surplus_kw, P_CHG_MAX, max_chg_from_soc)
                p_chg = max(0.0, p_chg)
            
            # Update Battery SOC State
            e_current = e_current + (p_chg * ETA_CHG - p_dis / ETA_DIS) * DELTA_T
            e_bat_day[t] = e_current
            
        # Daily Cost Accounting: c(t)*P_plan + 5*c(t)*P_em[cite: 2]
        daily_cost = np.sum((tariff_d * p_plan_kw + PENALTY_EMERGENCY * tariff_d * p_em_day) * DELTA_T)
        total_cost_all += daily_cost
        
        p_plan_all_kwh.extend(p_plan_kw * DELTA_T)
        p_em_all_kwh.extend(p_em_day * DELTA_T)
        e_bat_all_kwh.extend(e_bat_day)

    return {
        "p_plan_kwh": np.array(p_plan_all_kwh),
        "p_em_kwh": np.array(p_em_all_kwh),
        "e_bat_kwh": np.array(e_bat_all_kwh),
        "total_cost": total_cost_all
    }