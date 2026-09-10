import numpy as np

# System & Time Constants
DELTA_T = 1.0 / 6.0  # Time step: 10 minutes = 1/6 hour
STEPS_PER_DAY = 144  # 24 hours * 6 steps/hour

# Battery Energy Storage System (BESS) Specs
E_MAX = 10800.0      # Upper SOC limit (kWh) - 90% of 12000 kWh
E_MIN = 1200.0       # Lower SOC limit (kWh) - 10% of 12000 kWh
P_CHG_MAX = 5000.0   # Max Charge Power (kW)[cite: 2]
P_DIS_MAX = 5000.0   # Max Discharge Power (kW)[cite: 2]
ETA_CHG = 0.90       # Charging Efficiency (eta)[cite: 2]
ETA_DIS = 0.90       # Discharging Efficiency (eta)[cite: 2]
E_INIT = 6000.0      # Initial Battery Energy at 2025-01-01 00:00 (kWh)[cite: 2]

# Penalty Multipliers[cite: 2]
PENALTY_EMERGENCY = 5.0   # Emergency purchase penalty ratio[cite: 2]
PENALTY_ADD = 1.5         # Intra-day addition ratio (Q3)[cite: 2]
PENALTY_REDUCE = 0.5      # Intra-day reduction breach fee ratio (Q3)[cite: 2]

def get_baseline_load_forecast(historical_load_series, window_days=7):
    """
    Persistence / Rolling Average Forecast Rule for 0:00 Planning (Q2/Q3).
    """
    if len(historical_load_series) < window_days * STEPS_PER_DAY:
        # Fallback to simple persistence if historical window is short
        return historical_load_series[-STEPS_PER_DAY:]
    
    # 7-day rolling average for each 10-min slot of the day
    recent_history = historical_load_series[-(window_days * STEPS_PER_DAY):]
    reshaped = recent_history.reshape((window_days, STEPS_PER_DAY))
    return np.mean(reshaped, axis=0)