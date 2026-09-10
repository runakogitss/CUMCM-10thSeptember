import scipy.optimize as opt
import numpy as np
from src.config import (
    DELTA_T, STEPS_PER_DAY, E_MAX, E_MIN, 
    P_CHG_MAX, P_DIS_MAX, ETA_CHG, ETA_DIS, E_INIT
)
from src.data_loader import load_annex1_tariffs, load_annex2_actuals

def solve_q1():
    tariffs = load_annex1_tariffs()[:STEPS_PER_DAY]
    load_actual, pv_actual = load_annex2_actuals()
    
    load_d1 = load_actual[:STEPS_PER_DAY]
    pv_d1 = pv_actual[:STEPS_PER_DAY]
    
    T = STEPS_PER_DAY
    num_vars_per_t = 4  # P_grid(t), P_chg(t), P_dis(t), E_bat(t)
    num_vars = T * num_vars_per_t

    def idx(t, v): return t * num_vars_per_t + v

    # Objective: Min Sum(c(t) * P_grid(t) * Delta_t)[cite: 2]
    c = np.zeros(num_vars)
    for t in range(T):
        c[idx(t, 0)] = tariffs[t] * DELTA_T

    bounds = []
    for t in range(T):
        bounds.append((0, None))            # P_grid[cite: 2]
        bounds.append((0, P_CHG_MAX))       # P_chg[cite: 2]
        bounds.append((0, P_DIS_MAX))       # P_dis[cite: 2]
        bounds.append((E_MIN, E_MAX))       # E_bat[cite: 2]

    A_eq, b_eq = [], []
    for t in range(T):
        # Power Balance: P_grid + P_dis - P_chg = Load - PV[cite: 2]
        row_bal = np.zeros(num_vars)
        row_bal[idx(t, 0)] = 1.0
        row_bal[idx(t, 2)] = 1.0
        row_bal[idx(t, 1)] = -1.0
        A_eq.append(row_bal)
        b_eq.append(load_d1[t] - pv_d1[t])

        # SOC Dynamics: E(t) - E(t-1) - eta_chg*P_chg*dt + (1/eta_dis)*P_dis*dt = 0[cite: 2]
        row_soc = np.zeros(num_vars)
        row_soc[idx(t, 3)] = 1.0
        row_soc[idx(t, 1)] = -ETA_CHG * DELTA_T
        row_soc[idx(t, 2)] = (1.0 / ETA_DIS) * DELTA_T
        
        if t == 0:
            b_eq.append(E_INIT)
        else:
            row_soc[idx(t-1, 3)] = -1.0
            b_eq.append(0.0)

    # Boundary Condition: E(24:00) = E(0:00) = 6000 kWh[cite: 2]
    row_end = np.zeros(num_vars)
    row_end[idx(T-1, 3)] = 1.0
    A_eq.append(row_end)
    b_eq.append(E_INIT)

    res = opt.linprog(c, A_eq=np.array(A_eq), b_eq=np.array(b_eq), bounds=bounds, method='highs')
    
    # Extract kW decisions
    p_grid_kw = np.array([res.x[idx(t, 0)] for t in range(T)])
    p_chg_kw = np.array([res.x[idx(t, 1)] for t in range(T)])
    p_dis_kw = np.array([res.x[idx(t, 2)] for t in range(T)])
    e_bat_kwh = np.array([res.x[idx(t, 3)] for t in range(T)])

    return {
        "p_grid_kw": p_grid_kw,
        "p_chg_kw": p_chg_kw,
        "p_dis_kw": p_dis_kw,
        "e_bat_kwh": e_bat_kwh,
        "total_cost": res.fun
    }