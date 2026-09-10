from src.data_loader import (
    load_annex1_tariffs, load_annex2_actuals, 
    load_annex4_dynamic_tariffs, load_annex3_forecasts
)
from src.solver_q1 import solve_q1
from src.simulator_q2 import run_q2_simulation
from src.simulator_q3 import run_q3_simulation
from src.export_tools import export_result, export_q1_result

def main():
    print("=== Starting CUMCM 2026 Problem C Microgrid Optimization Pipeline ===")
    
    # 1. Question 1 Solution
    res_q1 = solve_q1()
    export_q1_result(res_q1)
    print(f"Q1 total electricity cost: {res_q1['total_cost']:.2f} yuan")
    print(f"Q1 total purchased energy: {res_q1['total_purchased_kwh']:.2f} kWh")
    print(f"Q1 terminal battery energy: {res_q1['terminal_energy']:.2f} kWh "
          f"(must equal {res_q1['e_bat_kwh'][-1]:.2f})")
    
    # 2. Question 2 Solution
    tariffs_q1 = load_annex1_tariffs()
    load_act, pv_act = load_annex2_actuals()
    res_q2 = run_q2_simulation(tariffs_q1, load_act, pv_act)
    export_result("result2.xlsx", {
        "P_plan_kWh": res_q2["p_plan_kwh"],
        "P_em_kWh": res_q2["p_em_kwh"],
        "E_bat_kWh": res_q2["e_bat_kwh"]
    })

    # 3. Question 3 Solution (intra-day adjustments with Annex 3 forecasts)
    pv_forecast = load_annex3_forecasts()
    res_q3 = run_q3_simulation(tariffs_q1, load_act, pv_act, pv_forecast)
    export_result("result3.xlsx", {
        "P_plan_kWh": res_q3["p_plan_kwh"],
        "P_adj_kWh": res_q3["p_adj_kwh"],
        "P_em_kWh": res_q3["p_em_kwh"],
        "E_bat_kWh": res_q3["e_bat_kwh"]
    })
    
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