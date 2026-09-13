import numpy as np
import scipy.optimize as opt
from src.config import (
    DELTA_T,
    STEPS_PER_DAY,
    E_MIN,
    E_MAX,
    P_DIS_MAX,
    P_CHG_MAX,
    ETA_DIS,
    ETA_CHG,
    E_INIT,
    PENALTY_EMERGENCY,
    SAFETY_BUFFER_ALPHA,
    FORECAST_WINDOW_DAYS,
    ROBUST_Z,
    E_PLAN_MIN,
    E_TERMINAL_TARGET,
    WARMUP_DAYS,
    SIM_START_DAY,
    SIM_NUM_DAYS,
    get_baseline_load_forecast,
    get_baseline_pv_forecast,
)

# Stage-1 LP 决策变量布局 (每时步 4 个变量: 0->P_plan, 1->P_chg, 2->P_dis, 3->E_bat)
STAGE1_VARS_PER_STEP = 4


def get_robust_net_load(
    historical_load,
    historical_pv,
    window_days=FORECAST_WINDOW_DAYS,
    z=ROBUST_Z,
):
    """
    构建日前鲁棒净负荷预测序列 (严格因果律，仅使用决策时刻前的历史数据)。
    """
    hist_load = np.asarray(historical_load, dtype=float)
    hist_pv = np.asarray(historical_pv, dtype=float)

    available_days = len(hist_load) // STEPS_PER_DAY
    window_days = int(min(window_days, available_days))
    if window_days < 1:
        return np.zeros(STEPS_PER_DAY)

    tail = window_days * STEPS_PER_DAY
    load_mat = hist_load[-tail:].reshape((window_days, STEPS_PER_DAY))
    pv_mat = hist_pv[-tail:].reshape((window_days, STEPS_PER_DAY))

    mu_load = load_mat.mean(axis=0)
    mu_pv = pv_mat.mean(axis=0)

    ddof = 1 if window_days > 1 else 0
    sig_load = load_mat.std(axis=0, ddof=ddof)
    sig_pv = pv_mat.std(axis=0, ddof=ddof)

    # 独立性假设下的两序列方差合成
    sig_net = np.sqrt(sig_load ** 2 + sig_pv ** 2)
    robust = mu_load - mu_pv + z * sig_net
    return np.maximum(0.0, robust)


def solve_stage1_lp(
    net_robust,
    tariff,
    e_start,
    e_plan_min=E_PLAN_MIN,
    e_terminal=E_TERMINAL_TARGET,
):
    """
    求解 144 步日前购电与储能调度线性规划 (LP)。
    目标: 最小化日前购电成本
    硬约束: 功率平衡、储能充放动态递推、容量/功率上下限、跨日储备终态约束
    """
    net_robust = np.asarray(net_robust, dtype=float)
    tariff = np.asarray(tariff, dtype=float)
    n = STEPS_PER_DAY
    nvars = STAGE1_VARS_PER_STEP * n

    def idx(t, v):
        return t * STAGE1_VARS_PER_STEP + v

    # 目标函数系数: min sum(c(t) * P_plan(t) * dt)
    c = np.zeros(nvars)
    for t in range(n):
        c[idx(t, 0)] = float(tariff[t]) * DELTA_T

    # 变量上下界
    bounds = []
    for t in range(n):
        bounds.append((0.0, None))              # P_plan
        bounds.append((0.0, P_CHG_MAX))         # P_chg
        bounds.append((0.0, P_DIS_MAX))         # P_dis
        if t == 0:
            bounds.append((min(e_plan_min, float(e_start)), E_MAX))
        else:
            bounds.append((e_plan_min, E_MAX))  # E_bat

    A_eq, b_eq = [], []
    for t in range(n):
        # 1. 功率平衡: P_plan + P_dis - P_chg = net_robust
        row = np.zeros(nvars)
        row[idx(t, 0)] = 1.0
        row[idx(t, 2)] = 1.0
        row[idx(t, 1)] = -1.0
        A_eq.append(row)
        b_eq.append(float(net_robust[t]))

        # 2. 电池动态递推: E_t - E_{t-1} = (eta_chg * P_chg - P_dis / eta_dis) * dt
        row = np.zeros(nvars)
        row[idx(t, 3)] = 1.0
        row[idx(t, 1)] = -ETA_CHG * DELTA_T
        row[idx(t, 2)] = DELTA_T / ETA_DIS
        if t > 0:
            row[idx(t - 1, 3)] = -1.0
        A_eq.append(row)
        b_eq.append(float(e_start if t == 0 else 0.0))

    # 3. 跨日末态储备约束: E(24:00) >= e_terminal
    A_ub, b_ub = [], []
    row = np.zeros(nvars)
    row[idx(n - 1, 3)] = -1.0
    A_ub.append(row)
    b_ub.append(-float(e_terminal))

    res = opt.linprog(
        c,
        A_eq=np.asarray(A_eq),
        b_eq=np.asarray(b_eq),
        A_ub=np.asarray(A_ub),
        b_ub=np.asarray(b_ub),
        bounds=bounds,
        method="highs",
    )
    if not res.success:
        raise RuntimeError(f"Q2 Stage-1 LP failed: {res.message}")

    p_plan = np.array([res.x[idx(t, 0)] for t in range(n)], dtype=float)
    return p_plan


def _real_time_dispatch(
    p_plan_d,
    load_act_d,
    pv_act_d,
    e_start,
):
    """
    单日 144 步日内物理调度与状态机推进。
    - 供电不足: 电池优先放电，不足差额触发 5 倍紧急购电
    - 供电富余: 优先充入电池，充满后物理弃光
    """
    p_plan_d = np.asarray(p_plan_d, dtype=float)
    load_act_d = np.asarray(load_act_d, dtype=float)
    pv_act_d = np.asarray(pv_act_d, dtype=float)

    e_current = float(e_start)
    p_em = np.zeros(STEPS_PER_DAY)
    p_chg = np.zeros(STEPS_PER_DAY)
    p_dis = np.zeros(STEPS_PER_DAY)
    e_bat = np.zeros(STEPS_PER_DAY)

    for t in range(STEPS_PER_DAY):
        deficit_kw = max(0.0, load_act_d[t] - (p_plan_d[t] + pv_act_d[t]))
        surplus_kw = max(0.0, (p_plan_d[t] + pv_act_d[t]) - load_act_d[t])

        p_dis_kw = 0.0
        p_chg_kw = 0.0

        if deficit_kw > 0.0:
            max_dis_from_soc = max(0.0, (e_current - E_MIN) * ETA_DIS / DELTA_T)
            p_dis_kw = min(deficit_kw, P_DIS_MAX, max_dis_from_soc)
            p_em[t] = deficit_kw - p_dis_kw
        elif surplus_kw > 0.0:
            max_chg_from_soc = max(0.0, (E_MAX - e_current) / (ETA_CHG * DELTA_T))
            p_chg_kw = min(surplus_kw, P_CHG_MAX, max_chg_from_soc)

        # 电池荷电状态闭环物理更新
        e_current = e_current + (p_chg_kw * ETA_CHG - p_dis_kw / ETA_DIS) * DELTA_T
        e_current = float(min(E_MAX, max(E_MIN, e_current)))

        p_chg[t] = p_chg_kw
        p_dis[t] = p_dis_kw
        e_bat[t] = e_current

    return p_em, p_chg, p_dis, e_bat, e_current


def run_q2_simulation(
    tariffs_matrix,
    load_actual_all,
    pv_actual_all,
    start_day=SIM_START_DAY,
    num_days=SIM_NUM_DAYS,
):
    """
    运行问题 2 两阶段鲁棒与套利优化模型。
    - 2025-01-01: E=6000 kWh 初值起步
    - 1 月份: 31 天自然预热，完全基于因果律生成 1 月末态
    - 2025-02-01 至 2025-12-31: 正式 334 天评测期仿真
    """
    if start_day < WARMUP_DAYS:
        raise ValueError(f"start_day must be >= WARMUP_DAYS ({WARMUP_DAYS}).")

    load_actual_all = np.asarray(load_actual_all, dtype=float)
    pv_actual_all = np.asarray(pv_actual_all, dtype=float)

    # 1 月份自然预热
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

    # 正式 334 天仿真
    total_cost_all = 0.0
    total_planned_cost = 0.0
    total_emergency_cost = 0.0

    p_plan_all_kwh = []
    p_em_all_kwh = []
    p_chg_all_kwh = []
    p_dis_all_kwh = []
    e_bat_all_kwh = []
    p_em_cost_all = []

    e_day_start = np.zeros(num_days)
    daily_plan_energy = np.zeros(num_days)
    daily_planned_cost = np.zeros(num_days)
    daily_emergency_cost = np.zeros(num_days)

    for d in range(num_days):
        day_idx = start_day + d
        t_start = day_idx * STEPS_PER_DAY
        t_end = t_start + STEPS_PER_DAY

        tariff_d = tariffs_matrix[day_idx] if np.ndim(tariffs_matrix) == 2 else tariffs_matrix
        load_act_d = np.asarray(load_actual_all[t_start:t_end], dtype=float)
        pv_act_d = np.asarray(pv_actual_all[t_start:t_end], dtype=float)

        net_robust = get_robust_net_load(
            load_actual_all[:t_start],
            pv_actual_all[:t_start],
        )
        p_plan_kw = solve_stage1_lp(net_robust, tariff_d, e_current)
        e_day_start[d] = e_current

        p_em_day, p_chg_day, p_dis_day, e_bat_day, e_current = _real_time_dispatch(
            p_plan_kw,
            load_act_d,
            pv_act_d,
            e_current,
        )

        planned_cost_day = float(np.sum(tariff_d * p_plan_kw * DELTA_T))
        emergency_cost_day = float(np.sum(PENALTY_EMERGENCY * tariff_d * p_em_day * DELTA_T))

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
        p_em_cost_all.extend(PENALTY_EMERGENCY * tariff_d * p_em_day * DELTA_T)

    p_plan_all_kwh = np.asarray(p_plan_all_kwh)
    p_em_all_kwh = np.asarray(p_em_all_kwh)
    p_chg_all_kwh = np.asarray(p_chg_all_kwh)
    p_dis_all_kwh = np.asarray(p_dis_all_kwh)
    e_bat_all_kwh = np.asarray(e_bat_all_kwh)
    p_em_cost_all = np.asarray(p_em_cost_all)

    return {
        "p_plan_kwh": p_plan_all_kwh,
        "p_em_kwh": p_em_all_kwh,
        "p_chg_kwh": p_chg_all_kwh,
        "p_dis_kwh": p_dis_all_kwh,
        "e_bat_kwh": e_bat_all_kwh,
        "p_em_cost": p_em_cost_all,
        "e_day_start": e_day_start,
        "daily_plan_energy": daily_plan_energy,
        "daily_planned_cost": daily_planned_cost,
        "daily_emergency_cost": daily_emergency_cost,
        "total_plan_kwh": float(np.sum(p_plan_all_kwh)),
        "total_em_kwh": float(np.sum(p_em_all_kwh)),
        "total_planned_cost": float(total_planned_cost),
        "total_emergency_cost": float(total_emergency_cost),
        "total_cost": float(total_cost_all),
        "warmup_end_soc": float(warmup_end_soc),
        "start_day": int(start_day),
        "num_days": int(num_days),
    }


def run_q2_baseline_simulation(
    tariffs_matrix,
    load_actual_all,
    pv_actual_all,
    start_day=SIM_START_DAY,
    num_days=SIM_NUM_DAYS,
):
    """
    运行启发式消极缓冲规则基线策略 (Baseline)。
    严格对齐 1 月份自然预热流程:
    两套策略均从 2025-01-01 00:00 (E=6000 kWh) 开始，按各自控制逻辑自然演化通过 1 月份，
    以真实的各自 1 月末态无缝切入正式 334 天仿真对比，保障评估基准公平性。
    """
    if start_day < WARMUP_DAYS:
        raise ValueError(f"start_day must be >= WARMUP_DAYS ({WARMUP_DAYS}).")

    load_actual_all = np.asarray(load_actual_all, dtype=float)
    pv_actual_all = np.asarray(pv_actual_all, dtype=float)

    # 1 月份自然预热 (基准策略自身演化)
    e_current = float(E_INIT)
    for d in range(start_day):
        t_start = d * STEPS_PER_DAY
        t_end = t_start + STEPS_PER_DAY

        tariff_d = tariffs_matrix[d] if np.ndim(tariffs_matrix) == 2 else tariffs_matrix
        load_pred_d = get_baseline_load_forecast(load_actual_all[:t_start])
        pv_pred_d = get_baseline_pv_forecast(pv_actual_all[:t_start])
        p_plan_kw = np.maximum(0.0, (load_pred_d - pv_pred_d) * SAFETY_BUFFER_ALPHA)

        load_act_d = np.asarray(load_actual_all[t_start:t_end], dtype=float)
        pv_act_d = np.asarray(pv_actual_all[t_start:t_end], dtype=float)

        _, _, _, _, e_current = _real_time_dispatch(
            p_plan_kw,
            load_act_d,
            pv_act_d,
            e_current,
        )

    baseline_warmup_end_soc = float(e_current)

    # 正式 334 天仿真
    total_cost_all = 0.0
    total_planned_cost = 0.0
    total_emergency_cost = 0.0
    total_plan_kwh = 0.0
    total_em_kwh = 0.0

    for d in range(num_days):
        day_idx = start_day + d
        t_start = day_idx * STEPS_PER_DAY
        t_end = t_start + STEPS_PER_DAY

        tariff_d = tariffs_matrix[day_idx] if np.ndim(tariffs_matrix) == 2 else tariffs_matrix
        load_act_d = np.asarray(load_actual_all[t_start:t_end], dtype=float)
        pv_act_d = np.asarray(pv_actual_all[t_start:t_end], dtype=float)

        load_pred_d = get_baseline_load_forecast(load_actual_all[:t_start])
        pv_pred_d = get_baseline_pv_forecast(pv_actual_all[:t_start])
        p_plan_kw = np.maximum(0.0, (load_pred_d - pv_pred_d) * SAFETY_BUFFER_ALPHA)

        p_em_day, p_chg_day, p_dis_day, e_bat_day, e_current = _real_time_dispatch(
            p_plan_kw,
            load_act_d,
            pv_act_d,
            e_current,
        )

        planned_cost_day = float(np.sum(tariff_d * p_plan_kw * DELTA_T))
        emergency_cost_day = float(np.sum(PENALTY_EMERGENCY * tariff_d * p_em_day * DELTA_T))

        total_planned_cost += planned_cost_day
        total_emergency_cost += emergency_cost_day
        total_cost_all += planned_cost_day + emergency_cost_day
        total_plan_kwh += float(np.sum(p_plan_kw * DELTA_T))
        total_em_kwh += float(np.sum(p_em_day * DELTA_T))

    return {
        "total_cost": float(total_cost_all),
        "total_planned_cost": float(total_planned_cost),
        "total_emergency_cost": float(total_emergency_cost),
        "total_plan_kwh": float(total_plan_kwh),
        "total_em_kwh": float(total_em_kwh),
        "warmup_end_soc": float(baseline_warmup_end_soc),
        "terminal_soc": float(e_current),
        "start_day": int(start_day),
        "num_days": int(num_days),
    }