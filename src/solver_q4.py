import numpy as np

from src.config import SIM_START_DAY, SIM_NUM_DAYS
from src.data_loader import (
    load_annex4_dynamic_tariffs, load_annex2_actuals, load_annex3_forecasts,
)
from src.simulator_q2 import run_q2_simulation
from src.mpc_q3 import run_q3_simulation
from src.export_tools import export_q4_2_result, export_q4_3_result


def solve_q4_2(tariffs_dynamic, load_actual_all, pv_actual_all,
               start_day=SIM_START_DAY, num_days=SIM_NUM_DAYS):
    """
    Q4-2: dynamic-tariff two-stage robust & arbitrage dispatch.

    Re-runs the Question 2 two-stage framework with the day-varying real-time
    tariff matrix c(d, t) from Attachment 4 instead of the static ToU tariff.
    """
    return run_q2_simulation(tariffs_dynamic, load_actual_all, pv_actual_all,
                             start_day=start_day, num_days=num_days)


def solve_q4_3(tariffs_dynamic, load_actual_all, pv_actual_all, pv_forecast_3d,
               start_day=SIM_START_DAY, num_days=SIM_NUM_DAYS):
    """
    Q4-3: dynamic-tariff multi-stage rolling MPC.

    Re-runs the Question 3 rolling-horizon MPC with the day-varying tariff
    matrix c(d, t) used at every intra-day epoch.
    """
    return run_q3_simulation(tariffs_dynamic, load_actual_all, pv_actual_all,
                             pv_forecast_3d, start_day=start_day, num_days=num_days)


def run_q4_pipeline(export=True):
    """
    Executes both Q4 pipelines (Q4-2 and Q4-3) under dynamic tariffs,
    exports the templated xlsx plus flat csv, and returns both result dicts.
    """
    tariffs_dynamic = load_annex4_dynamic_tariffs()
    load_act, pv_act = load_annex2_actuals()
    pv_forecast = load_annex3_forecasts()

    res_q4_2 = solve_q4_2(tariffs_dynamic, load_act, pv_act)
    res_q4_3 = solve_q4_3(tariffs_dynamic, load_act, pv_act, pv_forecast)

    if export:
        export_q4_2_result(res_q4_2)
        export_q4_3_result(res_q4_3, tariffs_dynamic)

    return res_q4_2, res_q4_3