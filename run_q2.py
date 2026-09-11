import pandas as pd

from src.data_loader import load_annex1_tariffs, load_annex2_actuals
from src.simulator_q2 import run_q2_simulation, run_q2_baseline_simulation
from src.export_tools import export_q2_result, verify_q2_export, RESULTS_DIR


def main():
    tariffs = load_annex1_tariffs()
    load_act, pv_act = load_annex2_actuals()

    print("Running baseline Q2 (passive buffer, no arbitrage)...")
    baseline_cost = run_q2_baseline_simulation(tariffs, load_act, pv_act)["total_cost"]

    print("Running two-stage robust & arbitrage Q2 (with Jan warm-up)...")
    res = run_q2_simulation(tariffs, load_act, pv_act)

    export_q2_result(res)
    verify_q2_export(f"{RESULTS_DIR}/Q2_optimized.xlsx", res["total_em_kwh"], res["total_cost"])

    savings = baseline_cost - res["total_cost"]
    summary = pd.DataFrame({
        "Metric": [
            "Baseline Q2 Cost (Yuan)",
            "Two-Stage Optimized Q2 Cost (Yuan)",
            "Cost Reduction (Yuan)",
            "Cost Reduction (%)",
            "Total Day-Ahead Planned Energy (kWh)",
            "Total Emergency Purchase Volume (kWh)",
            "Emergency Penalty Cost (Yuan)",
            "Warm-up end SOC at Jan 31 24:00 (kWh)",
        ],
        "Value": [
            round(baseline_cost, 2),
            round(res["total_cost"], 2),
            round(savings, 2),
            round(100.0 * savings / baseline_cost, 2),
            round(res["total_plan_kwh"], 2),
            round(res["total_em_kwh"], 2),
            round(res["total_emergency_cost"], 2),
            round(res["e_bat_kwh"][-1], 2),
        ],
    })
    print("\n=== Q2 Verification: Baseline vs Two-Stage Optimized ===")
    print(summary.to_string(index=False))

    summary.to_csv(f"{RESULTS_DIR}/Q2_optimized_summary.csv", index=False)
    summary.to_excel(f"{RESULTS_DIR}/Q2_optimized_summary.xlsx", index=False)
    print(f"[SUCCESS] Q2 summary saved to: {RESULTS_DIR}/Q2_optimized_summary.csv and .xlsx")


if __name__ == "__main__":
    main()