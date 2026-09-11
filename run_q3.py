import pandas as pd

from src.data_loader import load_annex1_tariffs, load_annex2_actuals, load_annex3_forecasts
from src.mpc_q3 import run_q3_simulation
from src.export_tools import export_result, RESULTS_DIR
from src.simulator_q2 import run_q2_simulation


def main():
    tariffs = load_annex1_tariffs()
    load_act, pv_act = load_annex2_actuals()
    pv_forecast = load_annex3_forecasts()

    res_q3 = run_q3_simulation(tariffs, load_act, pv_act, pv_forecast)
    export_result("result3.xlsx", {
        "P_plan_kWh": res_q3["p_plan_kwh"],
        "P_adj_kWh": res_q3["p_adj_kwh"],
        "P_em_kWh": res_q3["p_em_kwh"],
        "E_bat_kWh": res_q3["e_bat_kwh"]
    })

    res_q2 = run_q2_simulation(tariffs, load_act, pv_act)
    reduction = res_q2["total_cost"] - res_q3["total_cost"]
    reduction_pct = 100.0 * reduction / res_q2["total_cost"]
    summary = pd.DataFrame({
        "Metric": [
            "Total Day-Ahead Planned Energy (kWh)",
            "Total Adjusted Purchase Energy (kWh)",
            "Total Emergency Purchased Energy (kWh)",
            "Baseline Purchase Cost (Yuan)",
            "Adjustment Surcharge/Breach Cost (Yuan)",
            "Emergency Penalty Cost (Yuan)",
            "Total Settlement Cost Q3 (Yuan)",
            "Cost Reduction vs Q2 (Yuan)",
            "Cost Reduction vs Q2 (%)",
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

    summary.to_csv(f"{RESULTS_DIR}/q3_summary.csv", index=False)
    summary.to_excel(f"{RESULTS_DIR}/q3_summary.xlsx", index=False)
    print(f"[SUCCESS] Q3 summary saved to: {RESULTS_DIR}/q3_summary.csv and q3_summary.xlsx")


if __name__ == "__main__":
    main()