import os
import pandas as pd
import numpy as np
from scipy.interpolate import interp1d
from src.config import STEPS_PER_DAY

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")

def load_annex1_tariffs():
    """Loads time-of-use tariffs from Annex 1."""
    path = os.path.join(DATA_DIR, "Annex1.xlsx")
    df = pd.read_excel(path)
    return df.iloc[:, 1].values.astype(float)  # 144 steps tariff vector

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
    Loads Annex 3 PV forecasts (hourly) and interpolates to 10-min intervals[cite: 2].
    Forecasts updated at 0:00, 6:00, 12:00, 18:00[cite: 2].
    """
    path = os.path.join(DATA_DIR, "Annex3.xlsx")
    df = pd.read_excel(path)
    
    # Interpolate hourly forecast points to 10-min intervals
    hourly_pv = df.iloc[:, 1].values.astype(float)
    x_hourly = np.arange(len(hourly_pv))
    x_10min = np.linspace(0, len(hourly_pv) - 1, len(hourly_pv) * 6)
    
    f_interp = interp1d(x_hourly, hourly_pv, kind='cubic', fill_value='extrapolate')
    pv_forecast_10min = np.maximum(0.0, f_interp(x_10min))
    return pv_forecast_10min

def load_annex4_dynamic_tariffs():
    """Loads real-time dynamic electricity tariff matrix for Q4.

    Returns a (365, STEPS_PER_DAY) array (date column dropped).
    """
    path = os.path.join(DATA_DIR, "Annex4.xlsx")
    df = pd.read_excel(path)
    return df.iloc[:, 1:].values.astype(float)  # Shape: (Days, 144)