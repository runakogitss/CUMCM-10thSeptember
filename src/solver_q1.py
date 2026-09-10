import numpy as np
import scipy.optimize as opt
from src.config import (
    DELTA_T, STEPS_PER_DAY, E_MAX, E_MIN, 
    P_CHG_MAX, P_DIS_MAX, ETA_CHG, ETA_DIS, E_INIT
)
from src.data_loader import load_annex1_tariffs, load_annex2_actuals

def solve_q1():
    tariffs = load_annex1_tariffs()[:STEPS_PER_DAY]
    load_actual, pv_actual = load_annex2_actuals()
    
    # Ensure 1D scalar arrays
    load_d1 = np.asarray(load_actual[:STEPS_PER_DAY], dtype=float).flatten()
    pv_d1 = np.asarray(pv_actual[:STEPS_PER_DAY], dtype=float).flatten()
    
    T = STEPS_PER_DAY
    num_vars_per_t = 4  # 0: P_grid(t), 1: P_chg(t), 2: P_dis(t), 3: E_bat(t)
    num_vars = T * num_vars_per_t

    def idx(t, v): 
        return t * num_vars_per_t + v

    # Objective: Min Sum(c(t) * P_grid(t) * Delta_t)
    c = np.zeros(num_vars, dtype=float)
    for t in range(T):
        c[idx(t, 0)] = float(tariffs[t]) * DELTA_T

    # Decision Variable Bounds
    bounds = []
    for t in range(T):
        bounds.append((0, None))            # P_grid (kW)
        bounds.append((0, P_CHG_MAX))       # P_chg (kW)
        bounds.append((0, P_DIS_MAX))       # P_dis (kW)
        bounds.append((E_MIN, E_MAX))       # E_bat (kWh)

    A_eq_list = []
    b_eq_list = []

    for t in range(T):
        # 1. Power Balance Equation: P_grid + P_dis - P_chg = Load - PV
        row_bal = np.zeros(num_vars, dtype=float)
        row_bal[idx(t, 0)] = 1.0
        row_bal[idx(t, 2)] = 1.0
        row_bal[idx(t, 1)] = -1.0
        A_eq_list.append(row_bal)
        b_eq_list.append(float(load_d1[t] - pv_d1[t]))

        # 2. Battery SOC Dynamics: E(t) - E(t-1) - eta_chg*P_chg*dt + (1/eta_dis)*P_dis*dt = 0
        row_soc = np.zeros(num_vars, dtype=float)
        row_soc[idx(t, 3)] = 1.0
        row_soc[idx(t, 1)] = -ETA_CHG * DELTA_T
        row_soc[idx(t, 2)] = (1.0 / ETA_DIS) * DELTA_T
        A_eq_list.append(row_soc)

        if t == 0:
            b_eq_list.append(float(E_INIT))
        else:
            row_soc[idx(t-1, 3)] = -1.0
            b_eq_list.append(0.0)

    # 3. Daily Boundary Condition: E(24:00) = 6000 kWh
    row_end = np.zeros(num_vars, dtype=float)
    row_end[idx(T - 1, 3)] = 1.0
    A_eq_list.append(row_end)
    b_eq_list.append(float(E_INIT))

    # Convert strictly to 2D matrix and 1D vector
    A_eq = np.array(A_eq_list, dtype=float)
    b_eq = np.array(b_eq_list, dtype=float).reshape(-1)

    # Solve Linear Program
    res = opt.linprog(c, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')

    if not res.success:
        raise RuntimeError(f"Optimization failed: {res.message}")

    # Extract kW decision variables
    p_grid_kw = np.array([res.x[idx(t, 0)] for t in range(T)])
    p_chg_kw  = np.array([res.x[idx(t, 1)] for t in range(T)])
    p_dis_kw  = np.array([res.x[idx(t, 2)] for t in range(T)])
    e_bat_kwh = np.array([res.x[idx(t, 3)] for t in range(T)])

    return {
        "p_grid_kw": p_grid_kw,
        "p_chg_kw": p_chg_kw,
        "p_dis_kw": p_dis_kw,
        "e_bat_kwh": e_bat_kwh,
        "total_cost": res.fun
    }