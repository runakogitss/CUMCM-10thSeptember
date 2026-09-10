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
    """Loads 2025 full-year actual Load and PV power data (10-min resolution)."""
    path = os.path.join(DATA_DIR, "Annex2.xlsx")
    df = pd.read_excel(path)
    load_kw = df.iloc[:, 1].values.astype(float)
    pv_kw = df.iloc[:, 2].values.astype(float)
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
    """Loads real-time dynamic electricity tariff matrix for Q4."""
    path = os.path.join(DATA_DIR, "Annex4.xlsx")
    df = pd.read_excel(path)
    return df.values  # Shape: (Days, 144)