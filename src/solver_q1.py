import numpy as np
import scipy.optimize as opt
from src.config import (
    DELTA_T, STEPS_PER_DAY, E_MAX, E_MIN,
    P_CHG_MAX, P_DIS_MAX, ETA_CHG, ETA_DIS, E_INIT
)
from src.data_loader import load_annex1_data

def solve_q1():
    """
    Solves the deterministic day-ahead purchase problem (Question 1)
    using Annex 1 data only (price, load, PV forecast).

    Variables per step t in [0, 143]:
      0: P_grid(t) >= 0            (kW, grid purchase)
      1: P_curt(t) >= 0            (kW, solar curtailment slack)
      2: P_chg(t) in [0, P_CHG_MAX] (kW)
      3: P_dis(t) in [0, P_DIS_MAX] (kW)
      4: E_bat(t) in [E_MIN, E_MAX] (kWh)
    """
    price, load_kw, pv_kw = load_annex1_data()

    T = STEPS_PER_DAY
    num_vars_per_t = 5
    num_vars = T * num_vars_per_t

    def idx(t, v):
        return t * num_vars_per_t + v

    # Objective: Min sum(price(t) * P_grid(t) * DELTA_T)
    c = np.zeros(num_vars, dtype=float)
    for t in range(T):
        c[idx(t, 0)] = float(price[t]) * DELTA_T

    # Decision variable bounds
    bounds = []
    for t in range(T):
        bounds.append((0.0, None))          # P_grid
        bounds.append((0.0, None))          # P_curt
        bounds.append((0.0, P_CHG_MAX))     # P_chg
        bounds.append((0.0, P_DIS_MAX))     # P_dis
        bounds.append((E_MIN, E_MAX))       # E_bat

    A_eq = []
    b_eq = []

    for t in range(T):
        # 1. Power balance: P_grid - P_curt + P_dis - P_chg = load - pv
        row = np.zeros(num_vars, dtype=float)
        row[idx(t, 0)] = 1.0
        row[idx(t, 1)] = -1.0
        row[idx(t, 2)] = -1.0
        row[idx(t, 3)] = 1.0
        A_eq.append(row)
        b_eq.append(float(load_kw[t] - pv_kw[t]))

        # 2. SOC dynamics:
        #    E(t) - E(t-1) - eta_chg*P_chg*dt + (1/eta_dis)*P_dis*dt = 0
        row = np.zeros(num_vars, dtype=float)
        row[idx(t, 4)] = 1.0
        row[idx(t, 2)] = -ETA_CHG * DELTA_T
        row[idx(t, 3)] = (1.0 / ETA_DIS) * DELTA_T
        if t == 0:
            b_eq.append(float(E_INIT))
        else:
            row[idx(t - 1, 4)] = -1.0
            b_eq.append(0.0)
        A_eq.append(row)

    # 3. Terminal boundary: E(24:00) = E(0:00) = 6000 kWh
    row = np.zeros(num_vars, dtype=float)
    row[idx(T - 1, 4)] = 1.0
    A_eq.append(row)
    b_eq.append(float(E_INIT))

    # Solve Linear Program
    res = opt.linprog(c, A_eq=np.array(A_eq), b_eq=np.array(b_eq),
                      bounds=bounds, method='highs')

    if not res.success:
        raise RuntimeError(f"Optimization failed: {res.message}")

    # Extract decision variables
    p_grid_kw = np.array([res.x[idx(t, 0)] for t in range(T)])
    p_curt_kw = np.array([res.x[idx(t, 1)] for t in range(T)])
    p_chg_kw = np.array([res.x[idx(t, 2)] for t in range(T)])
    p_dis_kw = np.array([res.x[idx(t, 3)] for t in range(T)])
    e_bat_kwh = np.array([res.x[idx(t, 4)] for t in range(T)])

    return {
        "p_grid_kw": p_grid_kw,
        "p_curt_kw": p_curt_kw,
        "p_chg_kw": p_chg_kw,
        "p_dis_kw": p_dis_kw,
        "e_bat_kwh": e_bat_kwh,
        "total_cost": float(res.fun),
        "total_purchased_kwh": float(np.sum(p_grid_kw * DELTA_T)),
        "terminal_energy": float(e_bat_kwh[-1])
    }