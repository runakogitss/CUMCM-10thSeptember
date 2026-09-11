import os

import pandas as pd

from src.data_loader import (
    load_annex1_tariffs, load_annex2_actuals,
    load_annex4_dynamic_tariffs, load_annex3_forecasts,
    split_prior_and_simulation,
)
from src.solver_q1 import solve_q1
from src.simulator_q2 import run_q2_simulation
from src.mpc_q3 import run_q3_simulation
from src.export_tools import export_result, export_q1_result, export_q2_result, RESULTS_DIR


def _print_q3_summary(res, res_q2):
    reduction = res_q2["total_cost"] - res["total_cost"]
    reduction_pct = 100.0 * reduction / res_q2["total_cost"] if res_q2["total_cost"] else 0.0
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
            round(res["total_plan_kwh"], 2),
            round(res["total_adj_kwh"], 2),
            round(res["total_em_kwh"], 2),
            round(res["total_planned_cost"], 2),
            round(res["total_adjust_cost"], 2),
            round(res["total_emergency_cost"], 2),
            round(res["total_cost"], 2),
            round(reduction, 2),
            round(reduction_pct, 2),
        ],
    })
    print("\n=== Question 3 Summary (Rolling MPC) ===")
    print(summary.to_string(index=False))

    os.makedirs(RESULTS_DIR, exist_ok=True)
    summary_path = os.path.join(RESULTS_DIR, "q3_summary.csv")
    summary.to_csv(summary_path, index=False)
    summary_xlsx_path = os.path.join(RESULTS_DIR, "q3_summary.xlsx")
    summary.to_excel(summary_xlsx_path, index=False)
    print(f"[SUCCESS] Q3 summary saved to: {summary_path} and {summary_xlsx_path}")
    return summary


def _print_q2_summary(res):
    total_cost = res["total_cost"]
    emergency_share = 100.0 * res["total_emergency_cost"] / total_cost if total_cost else 0.0
    summary = pd.DataFrame({
        "Metric": [
            "Total Day-Ahead Planned Energy (kWh)",
            "Total Emergency Purchased Energy (kWh)",
            "Total Cost for Question 2 (Yuan)",
            "Emergency Penalty Percentage of Total Cost (%)",
        ],
        "Value": [
            round(res["total_plan_kwh"], 2),
            round(res["total_em_kwh"], 2),
            round(total_cost, 2),
            round(emergency_share, 2),
        ],
    })
    print("\n=== Question 2 Summary ===")
    print(summary.to_string(index=False))

    os.makedirs(RESULTS_DIR, exist_ok=True)
    summary_path = os.path.join(RESULTS_DIR, "q2_summary.csv")
    summary.to_csv(summary_path, index=False)
    summary_xlsx_path = os.path.join(RESULTS_DIR, "q2_summary.xlsx")
    summary.to_excel(summary_xlsx_path, index=False)
    print(f"[SUCCESS] Q2 summary saved to: {summary_path} and {summary_xlsx_path}")
    return summary


def main():
    print("=== Starting CUMCM 2026 Problem C Microgrid Optimization Pipeline ===")

    # 1. Question 1 Solution
    res_q1 = solve_q1()
    export_q1_result(res_q1)
    print(f"Q1 total electricity cost: {res_q1['total_cost']:.2f} yuan")
    print(f"Q1 total purchased energy: {res_q1['total_purchased_kwh']:.2f} kWh")
    print(f"Q1 terminal battery energy: {res_q1['terminal_energy']:.2f} kWh "
          f"(must equal {res_q1['e_bat_kwh'][-1]:.2f})")

    # 2. Question 2 Solution (Feb 1 - Dec 31 day-ahead commitment)
    tariffs_q1 = load_annex1_tariffs()
    load_act, pv_act = load_annex2_actuals()
    (load_prior, pv_prior), (load_sim, pv_sim) = split_prior_and_simulation(load_act, pv_act)
    print(f"Q2 prior window (January): {len(load_prior)} steps | "
          f"simulation window (Feb-Dec): {len(load_sim)} steps")

    res_q2 = run_q2_simulation(tariffs_q1, load_act, pv_act)
    export_q2_result(res_q2)
    _print_q2_summary(res_q2)

    # 3. Question 3 Solution (rolling-horizon MPC with Annex 3 PV forecasts)
    pv_forecast = load_annex3_forecasts()
    res_q3 = run_q3_simulation(tariffs_q1, load_act, pv_act, pv_forecast)
    export_result("result3.xlsx", {
        "P_plan_kWh": res_q3["p_plan_kwh"],
        "P_adj_kWh": res_q3["p_adj_kwh"],
        "P_em_kWh": res_q3["p_em_kwh"],
        "E_bat_kWh": res_q3["e_bat_kwh"]
    })
    _print_q3_summary(res_q3, res_q2)

    # 4. Question 4 (Dynamic Tariffs on Q2/Q3 Frameworks)
    dynamic_tariffs = load_annex4_dynamic_tariffs()
    res_q4_2 = run_q2_simulation(dynamic_tariffs, load_act, pv_act)
    export_result("result4-2.xlsx", {
        "P_plan_kWh": res_q4_2["p_plan_kwh"],
        "P_em_kWh": res_q4_2["p_em_kwh"],
        "E_bat_kWh": res_q4_2["e_bat_kwh"]
    })

    res_q4_3 = run_q3_simulation(dynamic_tariffs, load_act, pv_act, pv_forecast)
    export_result("result4-3.xlsx", {
        "P_plan_kWh": res_q4_3["p_plan_kwh"],
        "P_adj_kWh": res_q4_3["p_adj_kwh"],
        "P_em_kWh": res_q4_3["p_em_kwh"],
        "E_bat_kWh": res_q4_3["e_bat_kwh"]
    })

    print("=== All Question Pipelines Executed Successfully ===")


if __name__ == "__main__":
    main()
