import os
import pandas as pd

from src.data_loader import (
    load_annex1_tariffs,
    load_annex2_actuals,
    load_annex3_forecasts,
)
from src.mpc_q3 import run_q3_simulation
from src.export_tools import export_q3_result
from src.simulator_q2 import (
    run_q2_simulation,
    run_q2_baseline_simulation,
)


def main():
    # 1. 载入官方数据
    tariffs = load_annex1_tariffs()
    load_act, pv_act = load_annex2_actuals()
    pv_forecast = load_annex3_forecasts()

    # 2. 运行问题三闭环滚动 MPC 仿真
    print("Running Q3 rolling MPC (0:00 / 6:00 / 12:00 / 18:00 forecasts)...")
    res_q3 = run_q3_simulation(tariffs, load_act, pv_act, pv_forecast)

    # 3. 导出官方 result3.xlsx
    export_q3_result(res_q3, tariffs)

    # 4. 对比 Q2 鲁棒基准
    print("Running Q2 optimized benchmark...")
    res_q2 = run_q2_simulation(tariffs, load_act, pv_act)
    reduction_q2 = res_q2["total_cost"] - res_q3["total_cost"]
    reduction_pct_q2 = 100.0 * reduction_q2 / res_q2["total_cost"]

    # 5. 对比启发式基线
    print("Running heuristic baseline (with Jan warm-up)...")
    res_base = run_q2_baseline_simulation(tariffs, load_act, pv_act)
    baseline_cost = float(res_base["total_cost"])
    reduction_base = baseline_cost - res_q3["total_cost"]
    reduction_pct_base = 100.0 * reduction_base / baseline_cost

    # 6. 控制台打印结果汇总
    summary = pd.DataFrame({
        "Metric": [
            "Total Day-Ahead Planned Energy (kWh)",
            "Total Adjusted Purchase Energy (kWh)",
            "Total Emergency Purchased Energy (kWh)",
            "Baseline Purchase Cost (Yuan)",
            "Adjustment Surcharge/Breach Cost (Yuan)",
            "Emergency Penalty Cost (Yuan)",
            "Total Settlement Cost Q3 (Yuan)",
            "Cost Reduction vs Q2 Optimized (Yuan)",
            "Cost Reduction vs Q2 Optimized (%)",
            "Cost Reduction vs Heuristic Baseline (Yuan)",
            "Cost Reduction vs Heuristic Baseline (%)",
            "MPC Fallback Count",
            "MPC Terminal-Constraint Relax Count",
            "MPC Original-Plan Fallback Count",
        ],
        "Value": [
            round(res_q3["total_plan_kwh"], 2),
            round(res_q3["total_adj_kwh"], 2),
            round(res_q3["total_em_kwh"], 2),
            round(res_q3["total_planned_cost"], 2),
            round(res_q3["total_adjust_cost"], 2),
            round(res_q3["total_emergency_cost"], 2),
            round(res_q3["total_cost"], 2),
            round(reduction_q2, 2),
            round(reduction_pct_q2, 2),
            round(reduction_base, 2),
            round(reduction_pct_base, 2),
            int(res_q3["mpc_fallback_count"]),
            int(res_q3["mpc_terminal_relax_count"]),
            int(res_q3["mpc_plan_fallback_count"]),
        ],
    })

    print("\n=== Question 3 Summary (Rolling MPC) ===")
    print(summary.to_string(index=False))

    # 7. 控制台打印 MPC 可行性审计结论
    total_fallback = int(res_q3["mpc_fallback_count"])
    terminal_relax = int(res_q3["mpc_terminal_relax_count"])
    plan_fallback = int(res_q3["mpc_plan_fallback_count"])

    print("\n=== Q3 MPC Feasibility Audit ===")
    print(f"MPC fallback count: {total_fallback}")
    print(f"  Terminal-reserve relax count: {terminal_relax}")
    print(f"  Original-plan fallback count: {plan_fallback}")

    if total_fallback == 0:
        print("[PASS] All intra-day MPC optimizations were feasible with the original terminal reserve constraint.")
    else:
        print("[WARNING] One or more MPC fallback events occurred.")

    print("\n" f"[RESULT] Q3 total settlement cost: {res_q3['total_cost']:.2f} yuan")
    print(f"[COMPARE] vs Q2 Optimized: savings = {reduction_q2:.2f} yuan ({reduction_pct_q2:.2f}%)")
    print(f"[COMPARE] vs Heuristic Baseline: savings = {reduction_base:.2f} yuan ({reduction_pct_base:.2f}%)")


if __name__ == "__main__":
    main()