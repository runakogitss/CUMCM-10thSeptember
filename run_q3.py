import os
import pandas as pd

from src.data_loader import load_annex1_tariffs, load_annex2_actuals, load_annex3_forecasts
from src.mpc_q3 import run_q3_simulation
from src.export_tools import export_q3_result, RESULTS_DIR
from src.simulator_q2 import run_q2_baseline_simulation


def main():
    # 1. 加载官方基础数据 (data/raw/ 仅作为只读输入)
    tariffs = load_annex1_tariffs()
    load_act, pv_act = load_annex2_actuals()
    pv_forecast = load_annex3_forecasts()

    # 2. 运行 Q3 滚动预测控制 (MPC) 仿真 (2025.2.1 - 2025.12.31, 334天)
    res_q3 = run_q3_simulation(tariffs, load_act, pv_act, pv_forecast)

    # 3. 严格按照官方 Annex5_Templates/result3.xlsx 模板格式规范导出，
    #    同时生成 results/result3.xlsx 与 results/result3.csv
    export_q3_result(res_q3, tariffs)

    # 4. 运行 Q2 被动基线对比，计算信息价值增益与节费率
    baseline_cost = run_q2_baseline_simulation(tariffs, load_act, pv_act)["total_cost"]
    reduction = baseline_cost - res_q3["total_cost"]
    reduction_pct = 100.0 * reduction / baseline_cost

    # 5. 打印并持久化 Q3 宏观决策看板
    summary = pd.DataFrame({
        "Metric": [
            "Total Day-Ahead Planned Energy (kWh)",
            "Total Adjusted Purchase Energy (kWh)",
            "Total Emergency Purchased Energy (kWh)",
            "Baseline Purchase Cost (Yuan)",
            "Adjustment Surcharge/Breach Cost (Yuan)",
            "Emergency Penalty Cost (Yuan)",
            "Total Settlement Cost Q3 (Yuan)",
            "Cost Reduction vs Q2 Baseline (Yuan)",
            "Cost Reduction vs Q2 Baseline (%)",
        ],
        "Value": [
            round(res_q3["total_plan_kwh"], 2),
            round(res_q3["total_adj_kwh"], 2),
            round(res_q3["total_em_kwh"], 2),
            round(res_q3["total_planned_cost"], 2),
            round(res_q3["total_adjust_cost"], 2),
            round(res_q3["total_emergency_cost"], 2),
            round(res_q3["total_cost"], 2),
            round(reduction, 2),
            round(reduction_pct, 2),
        ],
    })
    print("\n=== Question 3 Summary (Rolling MPC) ===")
    print(summary.to_string(index=False))

    print(f"\n[RESULT] Q3 total settlement cost: {res_q3['total_cost']:.2f} yuan")
    print(f"[RESULT] Q2 baseline cost: {baseline_cost:.2f} yuan | "
          f"cost reduction: {reduction:.2f} yuan ({reduction_pct:.2f}%)")

    summary_csv = os.path.join(RESULTS_DIR, "q3_summary.csv")
    summary_xlsx = os.path.join(RESULTS_DIR, "q3_summary.xlsx")
    summary.to_csv(summary_csv, index=False)
    summary.to_excel(summary_xlsx, index=False)
    print(f"[SUCCESS] Q3 summary saved to: {summary_csv} and {summary_xlsx}")


if __name__ == "__main__":
    main()