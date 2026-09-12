import numpy as np
import scipy.optimize as opt

from src.config import (
    DELTA_T, STEPS_PER_DAY, E_MIN, E_MAX, P_CHG_MAX, P_DIS_MAX,
    ETA_CHG, ETA_DIS, E_INIT, PENALTY_ADD, PENALTY_REDUCE, PENALTY_EMERGENCY,
    E_TERMINAL_TARGET, WARMUP_DAYS, SIM_START_DAY, SIM_NUM_DAYS,
)
from src.simulator_q2 import get_robust_net_load, solve_stage1_lp, _real_time_dispatch

# 严格遵循赛题规范：仅在 6:00 (step 36), 12:00 (step 72), 18:00 (step 108) 触发滚动调整
INTRA_DAY_EPOCHS = (36, 72, 108)
ISSUE_HOUR_BY_EPOCH = {36: 6, 72: 12, 108: 18}

# 变量布局 (每步 8 个变量):
# 0: P_adj, 1: dP+, 2: dP-, 3: P_chg, 4: P_dis, 5: P_em, 6: P_curt, 7: E_bat
VARS_PER_STEP = 8


def solve_epoch_lp(p_plan_h, load_fc_h, tariff_h, soc_start, e_terminal=E_TERMINAL_TARGET):
    """
    求解日内 MPC 滚动时域线性规划 (t_now -> 144 步)。
    目标函数: min Σ (c·P_plan + 1.5c·ΔP+ - 0.5c·ΔP- + 5c·P_em)·Δt。
    其中 c·P_plan 为固定日前基础购电项(常数，不进入变量系数)；
    退调 ΔP- 按 0.5c 返回结算(贷方项)。
    约束满足功率平衡、电池物理边界与日末可持续性储备。
    """
    n = len(p_plan_h)
    nvars = VARS_PER_STEP * n

    def idx(t, v):
        return t * VARS_PER_STEP + v

    c = np.zeros(nvars)
    for t in range(n):
        c[idx(t, 1)] = PENALTY_ADD * tariff_h[t] * DELTA_T         # +1.5c ΔP+
        c[idx(t, 2)] = -PENALTY_REDUCE * tariff_h[t] * DELTA_T     # -0.5c ΔP- (credit)
        c[idx(t, 5)] = PENALTY_EMERGENCY * tariff_h[t] * DELTA_T   # +5c P_em

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
        # 1. 计划调整关系分解: P_adj(t) - P_plan(t) = dP+(t) - dP-(t)
        row = np.zeros(nvars)
        row[idx(t, 0)] = 1.0
        row[idx(t, 1)] = -1.0
        row[idx(t, 2)] = 1.0
        A_eq.append(row)
        b_eq.append(float(p_plan_h[t]))

        # 2. 功率动态平衡 (spec): P_adj + P_dis + P_em = P_load + P_chg - P_curt
        #    P_load 为净负荷预测 (load - pv)，即调用方传入的鲁棒净负荷 load_fc_h，
        #    P_curt 置于等式左侧并取负号 (弃电即供给侧损耗)。
        row = np.zeros(nvars)
        row[idx(t, 0)] = 1.0
        row[idx(t, 3)] = -1.0
        row[idx(t, 4)] = 1.0
        row[idx(t, 5)] = 1.0
        row[idx(t, 6)] = -1.0
        A_eq.append(row)
        b_eq.append(float(load_fc_h[t]))

        # 3. 储能 SoC 动态递推: E(t) - E(t-1) = (eta_chg * P_chg - P_dis / eta_dis) * dt
        row = np.zeros(nvars)
        row[idx(t, 7)] = 1.0
        row[idx(t, 3)] = -ETA_CHG * DELTA_T
        row[idx(t, 4)] = DELTA_T / ETA_DIS
        if t > 0:
            row[idx(t - 1, 7)] = -1.0
        A_eq.append(row)
        b_eq.append(float(soc_start if t == 0 else 0.0))

    # 4. 消除短视：设置日末储能储备软/硬边界约束，防止夜间将储能放空导致次日清晨击穿
    A_ub, b_ub = [], []
    row = np.zeros(nvars)
    row[idx(n - 1, 7)] = -1.0
    A_ub.append(row)
    b_ub.append(-float(e_terminal))

    res = opt.linprog(c, A_eq=np.array(A_eq), b_eq=np.array(b_eq),
                      A_ub=np.array(A_ub), b_ub=np.array(b_ub),
                      bounds=bounds, method="highs")
    
    # 极端不可行保护回退机制
    if not res.success:
        res = opt.linprog(c, A_eq=np.array(A_eq), b_eq=np.array(b_eq),
                          bounds=bounds, method="highs")
        if not res.success:
            return np.array(p_plan_h)

    return np.array([res.x[idx(t, 0)] for t in range(n)])


def run_q3_simulation(tariffs_matrix, load_actual_all, pv_actual_all,
                      pv_forecast_3d, start_day=SIM_START_DAY, num_days=SIM_NUM_DAYS):
    """
    问题 3 闭环滚动 MPC 仿真引擎 (2025.2.1 - 12.31，共 334 天)。
    
    1. 暖机对齐：严格执行 1 月份 (31天) 自然物理暖机，继承真实的 1月31日 24:00 残存电量；
    2. 日前计划：0:00 完全复用 Q2 的两阶段鲁棒 LP，确保基准成本与套利行为无缝对齐；
    3. 日内滚动：仅在 6:00、12:00、18:00 基于实际残存 SoC 与更新预报进行优化；
    4. 物理状态机：逐 10 分钟执行实时偏差吸收与 5 倍重罚结算。
    """
    if start_day < WARMUP_DAYS:
        raise ValueError("start_day 必须 >= 31，以保证 1 月份完成自然预热闭环")

    # --- 阶段 0: 1 月份 31 天无缝暖机预热 (与 Q2 完全一致) ---
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

    # --- 阶段 1: 2月1日 至 12月31日 逐日 MPC 滚动运行 ---
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

        # 0:00 决策时刻：严格继承 Q2 鲁棒净负荷与日前经济 LP
        net_robust = get_robust_net_load(load_actual_all[:t_start], pv_actual_all[:t_start])
        p_plan_kw = solve_stage1_lp(net_robust, tariff_d, e_current)

        # 初始执行序列：在 6:00 调整前，严格执行日前计划
        p_adj_final = p_plan_kw.copy()

        p_em_day = np.zeros(STEPS_PER_DAY)
        p_chg_day = np.zeros(STEPS_PER_DAY)
        p_dis_day = np.zeros(STEPS_PER_DAY)
        e_bat_day = np.zeros(STEPS_PER_DAY)

        # 逐 10 分钟状态机仿真
        for t in range(STEPS_PER_DAY):
            # 仅在 6:00, 12:00, 18:00 触发 MPC 滚动重规划
            if t in INTRA_DAY_EPOCHS:
                # 剩余时段滚动重排产 (基于鲁棒净负荷预测 net_robust，P_load = load - pv)
                p_adj_new = solve_epoch_lp(
                    p_plan_kw[t:], net_robust[t:],
                    tariff_d[t:], e_current,
                )
                p_adj_final[t:] = p_adj_new

            # 真实物理状态机执行 (基于当前锁定的 p_adj_final)
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

        # 每日结算费用计算
        dpp = np.maximum(0.0, p_adj_final - p_plan_kw)
        dpm = np.maximum(0.0, p_plan_kw - p_adj_final)

        planned_cost_day = float(np.sum(tariff_d * p_plan_kw * DELTA_T))
        adjust_cost_day = float(
            np.sum((PENALTY_ADD * tariff_d * dpp - PENALTY_REDUCE * tariff_d * dpm) * DELTA_T)
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
        "warmup_end_soc": e_current,
        "start_day": start_day,
        "num_days": num_days,
    }