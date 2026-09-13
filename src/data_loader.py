import os
import pandas as pd
import numpy as np
from src.config import STEPS_PER_DAY, PRIOR_STEPS, SIM_STEPS

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")

FORECAST_TIMES_HOURS = [0, 6, 12, 18]


def split_prior_and_simulation(load_kw, pv_kw):
    """Split the full-year Annex 2 actuals into prior and simulation windows.

    January 2025 (steps 0..4,463) is the prior/training set used by the
    forecasting models. February 1 - December 31 2025 (48,096 steps) is the
    Question 2 simulation and submission range.
    """
    prior = (load_kw[:PRIOR_STEPS], pv_kw[:PRIOR_STEPS])
    simulation = (load_kw[PRIOR_STEPS:PRIOR_STEPS + SIM_STEPS],
                  pv_kw[PRIOR_STEPS:PRIOR_STEPS + SIM_STEPS])
    return prior, simulation

def load_annex1_tariffs():
    """Loads time-of-use tariffs from Annex 1."""
    path = os.path.join(DATA_DIR, "Annex1.xlsx")
    df = pd.read_excel(path)
    return df.iloc[:, 1].values.astype(float)  # 144 steps tariff vector

def load_annex1_data():
    """Loads all four Annex 1 series as 1D float arrays of length 144.

    Returns (price, load_kw, pv_kw):
      * price  - column 1, electricity tariff (yuan/kWh)
      * load_kw - column 2, community load (kW)
      * pv_kw   - column 3, forecasted PV power (kW)
    """
    path = os.path.join(DATA_DIR, "Annex1.xlsx")
    df = pd.read_excel(path)
    price = df.iloc[:, 1].values.astype(float)
    load_kw = df.iloc[:, 2].values.astype(float)
    pv_kw = df.iloc[:, 3].values.astype(float)
    return price, load_kw, pv_kw

def load_annex2_actuals():
    """Loads 2025 full-year actual Load and PV power data (10-min resolution).

    Annex2 stores each series on its own sheet in wide format
    (365 days x 144 time steps). It is flattened to a single
    chronological vector of length 365 * STEPS_PER_DAY.
    """
    path = os.path.join(DATA_DIR, "Annex2.xlsx")
    load_df = pd.read_excel(path, sheet_name="小区负载")
    pv_df = pd.read_excel(path, sheet_name="光伏发电实际功率")
    load_kw = load_df.iloc[:, 1:].values.astype(float).reshape(-1)
    pv_kw = pv_df.iloc[:, 1:].values.astype(float).reshape(-1)
    return load_kw, pv_kw

def load_annex3_forecasts():
    """
    Loads Annex 3 PV forecasts into a (365, 4, 24) array.
    Axis 0: day index; axis 1: forecast issue time (0:00, 6:00, 12:00, 18:00);
    axis 2: hourly PV forecast for hour offset 0..23 from the issue time.
    """
    path = os.path.join(DATA_DIR, "Annex3.xlsx")
    df = pd.read_excel(path)

    dates = df["日期"].ffill()
    first_day = pd.to_datetime(dates.iloc[0])
    day_idx = (pd.to_datetime(dates) - first_day).dt.days.values
    fc = df.iloc[:, 2:].values.astype(float)  # (1460, 24) hourly values

    out = np.full((365, 4, 24), np.nan)
    for row, ft in enumerate(df["预报时刻"]):
        hour = int(str(ft).split(":")[0])
        ft_idx = FORECAST_TIMES_HOURS.index(hour)
        out[day_idx[row], ft_idx, :] = fc[row]
    return out


def get_pv_forecast_10min(fc_3d, day_idx, issue_hour):
    """
    Expands the hourly Annex3 forecast issued at `issue_hour` (0/6/12/18)
    to 144 ten-minute steps of the given day. Steps before the issue time
    (already elapsed) are returned as NaN.
    """
    ft_idx = FORECAST_TIMES_HOURS.index(issue_hour)
    fc_day = fc_3d[day_idx, ft_idx]  # (24,) hourly values from issue hour
    out = np.full(STEPS_PER_DAY, np.nan)
    start_step = issue_hour * 6  # 6 ten-minute steps per hour
    for step in range(start_step, STEPS_PER_DAY):
        hour_offset = (step - start_step) // 6
        out[step] = fc_day[hour_offset]
    return out

def load_annex4_dynamic_tariffs():
    """Loads real-time dynamic electricity tariff matrix for Q4.

    Returns a (365, STEPS_PER_DAY) array (date column dropped).
    """
    path = os.path.join(DATA_DIR, "Annex4.xlsx")
    df = pd.read_excel(path)
    return df.iloc[:, 1:].values.astype(float)  # Shape: (Days, 144)