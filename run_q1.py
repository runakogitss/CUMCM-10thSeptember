import pandas as pd

from src.solver_q1 import solve_q1
from src.export_tools import export_q1_result, RESULTS_DIR


def main():
    res = solve_q1()
    export_q1_result(res)

    summary = pd.DataFrame({
        "Metric": [
            "Total Electricity Cost (Yuan)",
            "Total Purchased Energy (kWh)",
            "Total Charge Energy (kWh)",
            "Total Discharge Energy (kWh)",
            "Terminal Battery Energy (kWh)",
        ],
        "Value": [
            round(res["total_cost"], 2),
            round(res["total_purchased_kwh"], 2),
            round(float((res["p_chg_kw"] * (1 / 6)).sum()), 2),
            round(float((res["p_dis_kw"] * (1 / 6)).sum()), 2),
            round(res["terminal_energy"], 2),
        ],
    })
    print("\n=== Question 1 Summary ===")
    print(summary.to_string(index=False))

    summary.to_csv(f"{RESULTS_DIR}/q1_summary.csv", index=False)
    summary.to_excel(f"{RESULTS_DIR}/q1_summary.xlsx", index=False)
    print(f"[SUCCESS] Q1 summary saved to: {RESULTS_DIR}/q1_summary.csv and .xlsx")


if __name__ == "__main__":
    main()