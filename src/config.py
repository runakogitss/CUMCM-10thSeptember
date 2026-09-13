import numpy as np

# System & Time Constants
DELTA_T = 1.0 / 6.0  # Time step: 10 minutes = 1/6 hour
STEPS_PER_DAY = 144  # 24 hours * 6 steps/hour

# Battery Energy Storage System (BESS) Specs
E_MAX = 10800.0      # Upper SOC limit (kWh) - 90% of 12000 kWh
E_MIN = 1200.0       # Lower SOC limit (kWh) - 10% of 12000 kWh
P_CHG_MAX = 5000.0   # Max Charge Power (kW)
P_DIS_MAX = 5000.0   # Max Discharge Power (kW)
ETA_CHG = 0.90       # Charging Efficiency (eta)
ETA_DIS = 0.90       # Discharging Efficiency (eta)
E_INIT = 6000.0      # Initial Battery Energy at 2025-01-01 00:00 (kWh)

# Penalty Multipliers
PENALTY_EMERGENCY = 5.0   # Emergency purchase penalty ratio
PENALTY_ADD = 1.5         # Intra-day addition ratio (Q3)
PENALTY_REDUCE = 0.5      # Intra-day reduction breach fee ratio (Q3)

# Question 2 day-ahead planning heuristics
FORECAST_WINDOW_DAYS = 7    # Rolling look-back window for the 0:00 forecast
SAFETY_BUFFER_ALPHA = 1.10

# Question 2 robust-planning parameters
ROBUST_Z = 0.625

# Planning-stage battery reserve threshold (kWh)
E_PLAN_MIN = 1700.0

# Desired minimum terminal battery reserve for day-ahead planning (kWh)
E_TERMINAL_TARGET = 4000.0
WARMUP_DAYS = 31            # January 1-31 prior warm-up window before Feb 1

# Simulation calendar (2025)
JANUARY_DAYS = 31                 # January prior/training window (days 1-31)
SIM_START_DAY = JANUARY_DAYS      # 0-indexed first simulation day (Feb 1)
SIM_NUM_DAYS = 334                # Feb 1 - Dec 31 inclusive
PRIOR_STEPS = JANUARY_DAYS * STEPS_PER_DAY   # 4,464 historical steps
SIM_STEPS = SIM_NUM_DAYS * STEPS_PER_DAY     # 48,096 simulation steps


def get_baseline_forecast(historical_series, window_days=FORECAST_WINDOW_DAYS):
    """
    Rolling persistence forecast used for 0:00 day-ahead planning (Q2/Q3).

    Averages the same 10-minute slot across the most recent `window_days`
    of available history, returning a 144-step forecast in the series units.
    """
    historical_series = np.asarray(historical_series, dtype=float)
    available_days = len(historical_series) // STEPS_PER_DAY
    window_days = int(min(window_days, available_days))
    if window_days < 1:
        return np.zeros(STEPS_PER_DAY)

    recent_history = historical_series[-(window_days * STEPS_PER_DAY):]
    reshaped = recent_history.reshape((window_days, STEPS_PER_DAY))
    return np.mean(reshaped, axis=0)


def get_baseline_load_forecast(historical_load_series, window_days=FORECAST_WINDOW_DAYS):
    """Day-ahead load forecast (kW) for each 10-minute slot."""
    return get_baseline_forecast(historical_load_series, window_days)


def get_baseline_pv_forecast(historical_pv_series, window_days=FORECAST_WINDOW_DAYS):
    """Day-ahead PV forecast (kW) for each 10-minute slot."""
    return get_baseline_forecast(historical_pv_series, window_days)