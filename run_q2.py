import os
import pandas as pd

from src.data_loader import load_annex1_tariffs, load_annex2_actuals
from src.simulator_q2 import run_q2_simulation, run_q2_baseline_simulation
from src.export_tools import export_q2_result, verify_q2_export, RESULTS_DIR


def main():
    tariffs = load_annex1_tariffs()
    load_act, pv_act = load_annex2_actuals()

    print("Running baseline Q2 (passive buffer, no arbitrage)...")
    res_base = run_q2_baseline_simulation(tariffs, load_act, pv_act)

    print("Running two-stage robust & arbitrage Q2 (with Jan warm-up)...")
    res_opt = run_q2_simulation(tariffs, load_act, pv_act)

    export_q2_result(res_opt)

    out_xlsx = os.path.join(RESULTS_DIR, "Q2_optimized.xlsx")
    verify_q2_export(out_xlsx, res_opt["total_em_kwh"], res_opt["total_cost"])

    baseline_cost = res_base["total_cost"]
    opt_cost = res_opt["total_cost"]
    savings = baseline_cost - opt_cost
    savings_pct = 100.0 * savings / baseline_cost

    # 关键修正：从 res_opt["warmup_end_soc"] 准确提取 1 月 31 日 24:00 真实暖机末态
    warmup_val = res_opt.get("warmup_end_soc", res_opt["e_bat_kwh"][0])

    summary_rows = [
        ("Baseline Q2 Cost (Yuan)", round(baseline_cost, 2)),
        ("Two-Stage Optimized Q2 Cost (Yuan)", round(opt_cost, 2)),
        ("Cost Reduction (Yuan)", round(savings, 2)),
        ("Cost Reduction (%)", round(savings_pct, 2)),
        ("Total Day-Ahead Planned Energy (kWh)", round(res_opt["total_plan_kwh"], 2)),
        ("Total Emergency Purchase Volume (kWh)", round(res_opt["total_em_kwh"], 2)),
        ("Emergency Penalty Cost (Yuan)", round(res_opt["total_emergency_cost"], 2)),
        ("Warm-up end SOC at Jan 31 24:00 (kWh)", round(warmup_val, 2)),
    ]

    summary_df = pd.DataFrame(summary_rows, columns=["Metric", "Value"])
    print("\n=== Q2 Verification: Baseline vs Two-Stage Optimized ===")
    print(summary_df.to_string(index=False))

    os.makedirs(RESULTS_DIR, exist_ok=True)
    csv_path = os.path.join(RESULTS_DIR, "Q2_optimized_summary.csv")
    xlsx_path = os.path.join(RESULTS_DIR, "Q2_optimized_summary.xlsx")
    summary_df.to_csv(csv_path, index=False)
    summary_df.to_excel(xlsx_path, index=False)
    print(f"[SUCCESS] Q2 summary saved to: {csv_path} and .xlsx")


if __name__ == "__main__":
    main()