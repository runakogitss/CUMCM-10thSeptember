import os
import pandas as pd

from src.data_loader import load_annex1_tariffs, load_annex2_actuals, load_annex3_forecasts
from src.mpc_q3 import run_q3_simulation
from src.export_tools import export_q3_result, RESULTS_DIR
from src.simulator_q2 import run_q2_simulation, run_q2_baseline_simulation


def main():
    # 1. 加载官方基础数据
    tariffs = load_annex1_tariffs()
    load_act, pv_act = load_annex2_actuals()
    pv_forecast = load_annex3_forecasts()

    # 2. 运行 Q3 滚动预测控制 (MPC) 仿真 (2025.2.1 - 2025.12.31, 334天)
    res_q3 = run_q3_simulation(tariffs, load_act, pv_act, pv_forecast)

    # 3. 严格按照官方 Annex5_Templates/result3.xlsx 模板规范导出 4 个工作表
    export_q3_result(res_q3, tariffs)

    # 4. 运行 Q2 优化基准对比，计算真实信息价值增益与节费率
    res_q2 = run_q2_simulation(tariffs, load_act, pv_act)
    reduction_q2 = res_q2["total_cost"] - res_q3["total_cost"]
    reduction_pct_q2 = 100.0 * reduction_q2 / res_q2["total_cost"]

    # 5. 同时对比未优化规则基准 (Baseline)
    baseline_cost = run_q2_baseline_simulation(tariffs, load_act, pv_act)["total_cost"]
    reduction_base = baseline_cost - res_q3["total_cost"]
    reduction_pct_base = 100.0 * reduction_base / baseline_cost

    # 6. 打印并持久化 Q3 宏观决策看板
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
        ],
    })
    print("\n=== Question 3 Summary (Rolling MPC) ===")
    print(summary.to_string(index=False))

    print(f"\n[RESULT] Q3 total settlement cost: {res_q3['total_cost']:.2f} yuan")
    print(f"[COMPARE] vs Q2 Optimized (16.08M): savings = {reduction_q2:.2f} yuan ({reduction_pct_q2:.2f}%)")
    print(f"[COMPARE] vs Heuristic Baseline (18.83M): savings = {reduction_base:.2f} yuan ({reduction_pct_base:.2f}%)")

    summary_csv = os.path.join(RESULTS_DIR, "q3_summary.csv")
    summary_xlsx = os.path.join(RESULTS_DIR, "q3_summary.xlsx")
    summary.to_csv(summary_csv, index=False)
    summary.to_excel(summary_xlsx, index=False)
    print(f"[SUCCESS] Q3 summary saved to: {summary_csv} and {summary_xlsx}")


if __name__ == "__main__":
    main()