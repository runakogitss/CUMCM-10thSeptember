import numpy as np
import scipy.optimize as opt

from src.config import (
    DELTA_T,
    STEPS_PER_DAY,
    E_MIN,
    E_MAX,
    P_CHG_MAX,
    P_DIS_MAX,
    ETA_CHG,
    ETA_DIS,
    E_INIT,
    PENALTY_ADD,
    PENALTY_REDUCE,
    PENALTY_EMERGENCY,
    E_PLAN_MIN,
    E_TERMINAL_TARGET,
    WARMUP_DAYS,
    SIM_START_DAY,
    SIM_NUM_DAYS,
    get_baseline_pv_forecast,
)
from src.data_loader import get_pv_forecast_10min
from src.simulator_q2 import (
    get_robust_net_load,
    solve_stage1_lp,
    _real_time_dispatch,
)

# 日内滚动调整断面时刻：6:00 (step 36), 12:00 (step 72), 18:00 (step 108)
INTRA_DAY_EPOCHS = (36, 72, 108)
ISSUE_HOUR_BY_EPOCH = {36: 6, 72: 12, 108: 18}

# 每时步决策变量布局 (共 8 个变量):
# 0: P_adj, 1: dP_plus, 2: dP_minus, 3: P_chg, 4: P_dis, 5: P_em, 6: P_curt, 7: E_bat
VARS_PER_STEP = 8


def solve_epoch_lp(
    p_plan_h,
    net_fc_h,
    tariff_h,
    soc_start,
    e_plan_min=E_PLAN_MIN,
    e_terminal=E_TERMINAL_TARGET,
    return_status=False,
):
    """
    求解日内 MPC 剩余时域滚动线性规划。
    采用三级受控回退防御体系保证递归可行性:
      - 状态 0: 主模型求解成功 (含终端荷电硬约束)
      - 状态 1: 一级回退成功 (松弛终端荷电储备约束)
      - 状态 2: 二级兜底保底 (沿用此前已签约的日前购电计划)
    """
    p_plan_h = np.asarray(p_plan_h, dtype=float)
    net_fc_h = np.asarray(net_fc_h, dtype=float)
    tariff_h = np.asarray(tariff_h, dtype=float)

    n = len(p_plan_h)
    nvars = VARS_PER_STEP * n

    def idx(t, v):
        return t * VARS_PER_STEP + v

    # 目标函数系数设置: min sum(1.5c*dP+ - 0.5c*dP- + 5c*P_em)*dt
    c = np.zeros(nvars)
    for t in range(n):
        c[idx(t, 1)] = PENALTY_ADD * tariff_h[t] * DELTA_T        # 增调购电成本 (+1.5c)
        c[idx(t, 2)] = -PENALTY_REDUCE * tariff_h[t] * DELTA_T   # 调减退电收益 (-0.5c)
        c[idx(t, 5)] = PENALTY_EMERGENCY * tariff_h[t] * DELTA_T # 紧急购电罚金 (+5c)

    # 物理变量上下限约束
    bounds = []
    for t in range(n):
        bounds.append((0.0, None))              # P_adj
        bounds.append((0.0, None))              # dP_plus
        bounds.append((0.0, None))              # dP_minus
        bounds.append((0.0, P_CHG_MAX))         # P_chg
        bounds.append((0.0, P_DIS_MAX))         # P_dis
        bounds.append((0.0, None))              # P_em
        bounds.append((0.0, None))              # P_curt
        # 储能荷电安全下限 (1700 kWh)
        if t == 0:
            bounds.append((min(e_plan_min, float(soc_start)), E_MAX))
        else:
            bounds.append((e_plan_min, E_MAX))

    # 等式约束矩阵
    A_eq = []
    b_eq = []
    for t in range(n):
        # 1. 计划调整分解关系: P_adj(t) - P_plan(t) = dP+(t) - dP-(t)
        row = np.zeros(nvars)
        row[idx(t, 0)] = 1.0
        row[idx(t, 1)] = -1.0
        row[idx(t, 2)] = 1.0
        A_eq.append(row)
        b_eq.append(float(p_plan_h[t]))

        # 2. 预测净负荷实时平衡: P_adj - P_chg + P_dis + P_em - P_curt = net_fc
        row = np.zeros(nvars)
        row[idx(t, 0)] = 1.0
        row[idx(t, 3)] = -1.0
        row[idx(t, 4)] = 1.0
        row[idx(t, 5)] = 1.0
        row[idx(t, 6)] = -1.0
        A_eq.append(row)
        b_eq.append(float(net_fc_h[t]))

        # 3. 储能动态递推方程: E(t) - E(t-1) = (eta_chg * P_chg - P_dis / eta_dis) * dt
        row = np.zeros(nvars)
        row[idx(t, 7)] = 1.0
        row[idx(t, 3)] = -ETA_CHG * DELTA_T
        row[idx(t, 4)] = DELTA_T / ETA_DIS
        if t > 0:
            row[idx(t - 1, 7)] = -1.0
        A_eq.append(row)
        b_eq.append(float(soc_start if t == 0 else 0.0))

    A_eq = np.asarray(A_eq)
    b_eq = np.asarray(b_eq)

    # 4. 终端荷电储备不等式约束: E(24:00) >= e_terminal
    A_ub = []
    b_ub = []
    row = np.zeros(nvars)
    row[idx(n - 1, 7)] = -1.0
    A_ub.append(row)
    b_ub.append(-float(e_terminal))
    A_ub = np.asarray(A_ub)
    b_ub = np.asarray(b_ub)

    # --- 阶段 1: 尝试求解主优化模型 ---
    res = opt.linprog(
        c,
        A_eq=A_eq,
        b_eq=b_eq,
        A_ub=A_ub,
        b_ub=b_ub,
        bounds=bounds,
        method="highs",
    )
    if res.success:
        p_adj = np.array([res.x[idx(t, 0)] for t in range(n)], dtype=float)
        return (p_adj, 0) if return_status else p_adj

    # --- 阶段 2: 一级受控回退 (仅松弛日末储备约束) ---
    res_relaxed = opt.linprog(
        c,
        A_eq=A_eq,
        b_eq=b_eq,
        bounds=bounds,
        method="highs",
    )
    if res_relaxed.success:
        p_adj = np.array([res_relaxed.x[idx(t, 0)] for t in range(n)], dtype=float)
        return (p_adj, 1) if return_status else p_adj

    # --- 阶段 3: 二级保底回退 (保持原日前排产计划) ---
    p_adj = np.array(p_plan_h, dtype=float)
    return (p_adj, 2) if return_status else p_adj


def run_q3_simulation(
    tariffs_matrix,
    load_actual_all,
    pv_actual_all,
    pv_forecast_3d=None,
    start_day=SIM_START_DAY,
    num_days=SIM_NUM_DAYS,
):
    """
    问题 3 闭环滚动 MPC 仿真引擎 (2025.02.01 - 2025.12.31，共 334 天)。
    严格满足 1 月份自然预热，并在 0:00/6:00/12:00/18:00 全面吸收附件 3 预报信息。
    """
    if start_day < WARMUP_DAYS:
        raise ValueError(f"start_day must be >= WARMUP_DAYS ({WARMUP_DAYS}).")

    load_actual_all = np.asarray(load_actual_all, dtype=float)
    pv_actual_all = np.asarray(pv_actual_all, dtype=float)

    # 阶段 0: 1 月份 31 天无缝暖机预热
    e_current = float(E_INIT)
    for d in range(start_day):
        t_start = d * STEPS_PER_DAY
        t_end = t_start + STEPS_PER_DAY
        tariff_d = tariffs_matrix[d] if np.ndim(tariffs_matrix) == 2 else tariffs_matrix

        net_robust = get_robust_net_load(
            load_actual_all[:t_start],
            pv_actual_all[:t_start],
        )
        p_plan_d = solve_stage1_lp(net_robust, tariff_d, e_current)

        _, _, _, _, e_current = _real_time_dispatch(
            p_plan_d,
            load_actual_all[t_start:t_end],
            pv_actual_all[t_start:t_end],
            e_current,
        )

    warmup_end_soc = float(e_current)

    # 阶段 1: 正式 334 天逐日 MPC 滚动运行
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
    e_day_start = np.zeros(num_days)

    # 审计记录器
    terminal_relax_count = 0
    plan_fallback_count = 0
    fallback_events = []

    for d in range(num_days):
        day_idx = start_day + d
        t_start = day_idx * STEPS_PER_DAY
        t_end = t_start + STEPS_PER_DAY

        tariff_d = tariffs_matrix[day_idx] if np.ndim(tariffs_matrix) == 2 else tariffs_matrix
        load_act_d = np.asarray(load_actual_all[t_start:t_end], dtype=float)
        pv_act_d = np.asarray(pv_actual_all[t_start:t_end], dtype=float)

        e_day_start[d] = e_current

        # 0:00 基础鲁棒净负荷与历史光伏基线
        net_robust = get_robust_net_load(
            load_actual_all[:t_start],
            pv_actual_all[:t_start],
        )
        mu_pv_baseline = get_baseline_pv_forecast(
            pv_actual_all[:t_start]
        )

        # 0:00 消费附件 3 当天首发预报进行信度收缩 (beta=0.20)
        if pv_forecast_3d is not None:
            pv_fc_0 = get_pv_forecast_10min(pv_forecast_3d, day_idx, 0)
            pv_fc_0 = np.nan_to_num(pv_fc_0, nan=0.0)
            pv_diff_0 = pv_fc_0 - mu_pv_baseline
            net_fc_0 = np.maximum(0.0, net_robust - 0.20 * pv_diff_0)
        else:
            net_fc_0 = net_robust

        p_plan_kw = solve_stage1_lp(net_fc_0, tariff_d, e_current)
        p_adj_final = p_plan_kw.copy()

        p_em_day = np.zeros(STEPS_PER_DAY)
        p_chg_day = np.zeros(STEPS_PER_DAY)
        p_dis_day = np.zeros(STEPS_PER_DAY)
        e_bat_day = np.zeros(STEPS_PER_DAY)

        # 逐 10 分钟状态机推进与日内整点滚动
        for t in range(STEPS_PER_DAY):
            # 在 6:00, 12:00, 18:00 提取最新发布预报并重解 LP
            if t in INTRA_DAY_EPOCHS:
                if pv_forecast_3d is not None:
                    issue_h = ISSUE_HOUR_BY_EPOCH[t]
                    pv_fc_epoch = get_pv_forecast_10min(pv_forecast_3d, day_idx, issue_h)
                    pv_fc_epoch = np.nan_to_num(pv_fc_epoch, nan=0.0)
                    pv_diff = pv_fc_epoch[t:] - mu_pv_baseline[t:]
                    net_fc_intra = np.maximum(0.0, net_robust[t:] - 0.20 * pv_diff)
                else:
                    net_fc_intra = net_robust[t:]

                p_adj_new, fallback_status = solve_epoch_lp(
                    p_plan_kw[t:],
                    net_fc_intra,
                    tariff_d[t:],
                    e_current,
                    return_status=True,
                )

                # 记录审计回退状态
                if fallback_status == 1:
                    terminal_relax_count += 1
                    fallback_events.append({
                        "simulation_day_index": int(d),
                        "calendar_day_index": int(day_idx),
                        "issue_hour": int(ISSUE_HOUR_BY_EPOCH[t]),
                        "status": "terminal_constraint_relaxed",
                    })
                elif fallback_status == 2:
                    plan_fallback_count += 1
                    fallback_events.append({
                        "simulation_day_index": int(d),
                        "calendar_day_index": int(day_idx),
                        "issue_hour": int(ISSUE_HOUR_BY_EPOCH[t]),
                        "status": "original_plan_retained",
                    })

                p_adj_final[t:] = p_adj_new

            # 真实物理状态机偏差吸收
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

            e_current = e_current + (p_chg * ETA_CHG - p_dis / ETA_DIS) * DELTA_T
            e_current = float(min(E_MAX, max(E_MIN, e_current)))

            p_chg_day[t] = p_chg
            p_dis_day[t] = p_dis
            e_bat_day[t] = e_current

        # 每日增减调与结算核算
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
    p_chg_all_kwh = np.asarray(p_chg_all_kwh)
    p_dis_all_kwh = np.asarray(p_dis_all_kwh)
    e_bat_all_kwh = np.asarray(e_bat_all_kwh)

    fallback_count = terminal_relax_count + plan_fallback_count

    return {
        "p_plan_kwh": p_plan_all_kwh,
        "p_adj_kwh": p_adj_all_kwh,
        "p_em_kwh": p_em_all_kwh,
        "p_chg_kwh": p_chg_all_kwh,
        "p_dis_kwh": p_dis_all_kwh,
        "e_bat_kwh": e_bat_all_kwh,
        "e_day_start": e_day_start,
        "total_plan_kwh": float(np.sum(p_plan_all_kwh)),
        "total_adj_kwh": float(np.sum(p_adj_all_kwh)),
        "total_em_kwh": float(np.sum(p_em_all_kwh)),
        "total_planned_cost": float(total_planned_cost),
        "total_adjust_cost": float(total_adjust_cost),
        "total_emergency_cost": float(total_emergency_cost),
        "total_cost": float(total_cost_all),
        "warmup_end_soc": float(warmup_end_soc),
        "start_day": int(start_day),
        "num_days": int(num_days),
        # 核心审计指标
        "mpc_fallback_count": int(fallback_count),
        "mpc_terminal_relax_count": int(terminal_relax_count),
        "mpc_plan_fallback_count": int(plan_fallback_count),
        "mpc_fallback_events": fallback_events,
    }