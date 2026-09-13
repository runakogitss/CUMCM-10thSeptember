import numpy as np
import pandas as pd

from src.data_loader import (
    load_annex1_tariffs, load_annex2_actuals, load_annex3_forecasts,
    load_annex4_dynamic_tariffs,
)
from src.simulator_q2 import run_q2_simulation
from src.mpc_q3 import run_q3_simulation
from src.export_tools import export_q4_2_result, export_q4_3_result


def _sensitivity(tariffs_dynamic, res_q4_2):
    sim_tar = tariffs_dynamic[31:, :]
    mean_dyn = float(sim_tar.mean())
    max_dyn = float(sim_tar.max())
    peak_idx = np.unravel_index(np.argmax(sim_tar), sim_tar.shape)
    peak_day, peak_step = peak_idx[0] + 1, peak_idx[1]
    hours, minutes = divmod(peak_step * 10, 60)

    top_decile = np.quantile(sim_tar, 0.90)
    bot_decile = np.quantile(sim_tar, 0.10)
    dis_high = float(np.sum(res_q4_2["p_dis_kwh"][sim_tar.ravel() > top_decile]))
    chg_low = float(np.sum(res_q4_2["p_chg_kwh"][sim_tar.ravel() < bot_decile]))
    em_high = float(np.sum(res_q4_2["p_em_kwh"][sim_tar.ravel() > top_decile]))

    return {
        "Mean dynamic tariff (Yuan/kWh)": round(mean_dyn, 4),
        "Max dynamic tariff (Yuan/kWh)": round(max_dyn, 4),
        "Peak tariff day/hour": f"Day {peak_day} {hours}:{minutes:02d}",
        "Battery discharge in top-10% tariff hours (kWh)": round(dis_high, 2),
        "Battery charge in bottom-10% tariff hours (kWh)": round(chg_low, 2),
        "Emergency energy in top-10% tariff hours (kWh)": round(em_high, 2),
    }


def main():
    tariffs_static = load_annex1_tariffs()
    tariffs_dynamic = load_annex4_dynamic_tariffs()
    load_act, pv_act = load_annex2_actuals()
    pv_forecast = load_annex3_forecasts()

    print("Running Q4-2 dynamic-tariff two-stage dispatch...")
    res_q4_2 = run_q2_simulation(tariffs_dynamic, load_act, pv_act)
    print("Running Q4-3 dynamic-tariff rolling MPC...")
    res_q4_3 = run_q3_simulation(tariffs_dynamic, load_act, pv_act, pv_forecast)

    print("Running static-tariff baselines for comparison...")
    res_static_2 = run_q2_simulation(tariffs_static, load_act, pv_act)
    res_static_3 = run_q3_simulation(tariffs_static, load_act, pv_act, pv_forecast)

    # 仅导出官方指定的两份 .xlsx 文件
    export_q4_2_result(res_q4_2)
    export_q4_3_result(res_q4_3, tariffs_dynamic)

    rows = [
        ("Q4-2 Static-Tariff Cost (Yuan)", round(res_static_2["total_cost"], 2)),
        ("Q4-2 Dynamic-Tariff Cost (Yuan)", round(res_q4_2["total_cost"], 2)),
        ("Q4-2 Cost Change (%)", round(100.0 * (res_q4_2["total_cost"] - res_static_2["total_cost"]) / res_static_2["total_cost"], 2)),
        ("Q4-2 Emergency Volume (kWh)", round(res_q4_2["total_em_kwh"], 2)),
        ("Q4-2 Emergency Penalty (Yuan)", round(res_q4_2["total_emergency_cost"], 2)),
        ("Q4-3 Static-Tariff Cost (Yuan)", round(res_static_3["total_cost"], 2)),
        ("Q4-3 Dynamic-Tariff Cost (Yuan)", round(res_q4_3["total_cost"], 2)),
        ("Q4-3 Cost Change (%)", round(100.0 * (res_q4_3["total_cost"] - res_static_3["total_cost"]) / res_static_3["total_cost"], 2)),
        ("Q4-3 Emergency Volume (kWh)", round(res_q4_3["total_em_kwh"], 2)),
        ("Q4-3 Emergency Penalty (Yuan)", round(res_q4_3["total_emergency_cost"], 2)),
    ]
    summary = pd.DataFrame({"Metric": [r[0] for r in rows], "Value": [r[1] for r in rows]})
    print("\n=== Question 4 Comparative Summary (Dynamic vs Static Tariffs) ===")
    print(summary.to_string(index=False))

    sens = pd.DataFrame(_sensitivity(tariffs_dynamic, res_q4_2).items(), columns=["Metric", "Value"])
    print("\n=== Q4 Sensitivity Highlights (Annex 4 Peak Price Spikes) ===")
    print(sens.to_string(index=False))


if __name__ == "__main__":
    main()