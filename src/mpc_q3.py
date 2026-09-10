import numpy as np
import scipy.optimize as opt
from src.config import DELTA_T, STEPS_PER_DAY, PENALTY_ADD, PENALTY_REDUCE, PENALTY_EMERGENCY

def run_q3_mpc_step(p_plan_kw, p_pv_updated_kw, c_tariff):
    """
    Solves intra-day adjustment P_adj(t) given newly arrived forecasts[cite: 2].
    Surcharge breakdown: 1.5x for additions, 0.5x breach fee for reductions[cite: 2].
    """
    T = len(p_plan_kw)
    # Vars per t: P_adj(t), Delta_P_plus(t), Delta_P_minus(t)
    num_vars = T * 3
    def idx(t, v): return t * 3 + v

    c = np.zeros(num_vars)
    for t in range(T):
        c[idx(t, 1)] = PENALTY_ADD * c_tariff[t] * DELTA_T     # 1.5 * c(t)[cite: 2]
        c[idx(t, 2)] = PENALTY_REDUCE * c_tariff[t] * DELTA_T  # 0.5 * c(t)[cite: 2]

    bounds = []
    for t in range(T):
        bounds.append((0, None))  # P_adj
        bounds.append((0, None))  # Delta_P_plus
        bounds.append((0, None))  # Delta_P_minus

    A_eq, b_eq = [], []
    for t in range(T):
        # P_adj(t) - P_plan(t) = Delta_P_plus(t) - Delta_P_minus(t)[cite: 2]
        row = np.zeros(num_vars)
        row[idx(t, 0)] = 1.0
        row[idx(t, 1)] = -1.0
        row[idx(t, 2)] = 1.0
        A_eq.append(row)
        b_eq.append(p_plan_kw[t])

    res = opt.linprog(c, A_eq=np.array(A_eq), b_eq=np.array(b_eq), bounds=bounds, method='highs')
    
    p_adj_kw = np.array([res.x[idx(t, 0)] for t in range(T)])
    return p_adj_kw