import numpy as np
import pandas as pd

import src.simulator_q2 as sim_q2
from src.data_loader import load_annex1_tariffs, load_annex2_actuals


# 需要测试的鲁棒安全系数
Z_VALUES = [0.0, 0.25, 0.50, 0.625, 0.75, 1.00]


def main():
    tariffs = load_annex1_tariffs()
    load_act, pv_act = load_annex2_actuals()

    original_function = sim_q2.get_robust_net_load

    results = []

    for z_value in Z_VALUES:

        print(f"\n===== Running z = {z_value:.3f} =====")

        # 临时替换鲁棒净负荷函数，使本轮仿真使用指定 z
        def robust_with_fixed_z(
            historical_load,
            historical_pv,
            window_days=sim_q2.FORECAST_WINDOW_DAYS,
            z=None
        ):
            return original_function(
                historical_load,
                historical_pv,
                window_days=window_days,
                z=z_value
            )

        sim_q2.get_robust_net_load = robust_with_fixed_z

        res = sim_q2.run_q2_simulation(
            tariffs,
            load_act,
            pv_act
        )

        results.append({
            "z": z_value,
            "planned_energy_kWh": res["total_plan_kwh"],
            "planned_cost_yuan": res["total_planned_cost"],
            "emergency_energy_kWh": res["total_em_kwh"],
            "emergency_cost_yuan": res["total_emergency_cost"],
            "total_cost_yuan": res["total_cost"],
        })

        print(
            f"z={z_value:.3f} | "
            f"Plan Cost={res['total_planned_cost']:.2f} | "
            f"Emergency Cost={res['total_emergency_cost']:.2f} | "
            f"Total={res['total_cost']:.2f} | "
            f"Emergency={res['total_em_kwh']:.2f} kWh"
        )

    # 恢复原函数
    sim_q2.get_robust_net_load = original_function

    df = pd.DataFrame(results)

    print("\n===== Q2 z Sensitivity Summary =====")
    print(df.to_string(index=False))

    df.to_csv(
        "results/q2_z_sensitivity.csv",
        index=False,
        encoding="utf-8-sig"
    )

    df.to_excel(
        "results/q2_z_sensitivity.xlsx",
        index=False
    )

    print("\nSaved:")
    print("results/q2_z_sensitivity.csv")
    print("results/q2_z_sensitivity.xlsx")


if __name__ == "__main__":
    main()