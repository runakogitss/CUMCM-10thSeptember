from src.data_loader import (
    load_annex1_tariffs, load_annex2_actuals, 
    load_annex4_dynamic_tariffs
)
from src.solver_q1 import solve_q1
from src.simulator_q2 import run_q2_simulation
from src.export_tools import export_result

def main():
    print("=== Starting CUMCM 2026 Problem C Microgrid Optimization Pipeline ===")
    
    # 1. Question 1 Solution
    res_q1 = solve_q1()
    export_result("result1.xlsx", {
        "Grid_Purchase_kWh": res_q1["p_grid_kw"] * (1/6),
        "Battery_Charge_kWh": res_q1["p_chg_kw"] * (1/6),
        "Battery_Discharge_kWh": res_q1["p_dis_kw"] * (1/6),
        "Battery_SOC_kWh": res_q1["e_bat_kwh"]
    })
    
    # 2. Question 2 Solution
    tariffs_q1 = load_annex1_tariffs()
    load_act, pv_act = load_annex2_actuals()
    res_q2 = run_q2_simulation(tariffs_q1, load_act, pv_act)
    export_result("result2.xlsx", {
        "P_plan_kWh": res_q2["p_plan_kwh"],
        "P_em_kWh": res_q2["p_em_kwh"],
        "E_bat_kWh": res_q2["e_bat_kwh"]
    })
    
    # 3. Question 4 (Dynamic Tariffs on Q2 Framework)[cite: 2]
    dynamic_tariffs = load_annex4_dynamic_tariffs()
    res_q4_2 = run_q2_simulation(dynamic_tariffs, load_act, pv_act)
    export_result("result4-2.xlsx", {
        "P_plan_kWh": res_q4_2["p_plan_kwh"],
        "P_em_kWh": res_q4_2["p_em_kwh"],
        "E_bat_kWh": res_q4_2["e_bat_kwh"]
    })
    
    print("=== All Question Pipelines Executed Successfully ===")

if __name__ == "__main__":
    main()