import os
import numpy as np
import pandas as pd
from openpyxl import load_workbook

from src.config import DELTA_T, E_INIT

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "Annex5_Templates")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")

# 4-hour aggregation windows: (start_step, end_step) exclusive end.
FOUR_HOUR_WINDOWS = [
    (0, 24), (24, 48), (48, 72), (72, 96), (96, 120), (120, 144),
]


def _ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def export_q1_result(res):
    """
    Populates the blank Annex 5 result1 template (never modifying the raw
    template) and saves the populated workbook to results/result1.xlsx.

    Sheet "计划购电量": 144 rows of P_grid(t) * DELTA_T (kWh), rows 2-145, col 2.
    Sheet "充放电量":
      * Rows 2-7: charge/discharge energy (kWh) per 4-hour window.
      * Row 8:    col 2 = E(0) = 6000.0, col 3 = E(143) terminal energy.
    """
    template_path = os.path.join(TEMPLATES_DIR, "result1.xlsx")
    out_path = os.path.join(RESULTS_DIR, "result1.xlsx")
    _ensure_dir(RESULTS_DIR)

    wb = load_workbook(template_path)

    # Sheet 1: planned grid purchase energy per 10-min step
    ws = wb["计划购电量"]
    for t in range(len(res["p_grid_kw"])):
        ws.cell(row=2 + t, column=2, value=float(res["p_grid_kw"][t]) * DELTA_T)

    # Sheet 2: 4-hour aggregated charge/discharge + terminal SOC
    ws = wb["充放电量"]
    for i, (a, b) in enumerate(FOUR_HOUR_WINDOWS):
        chg = float(np.sum(res["p_chg_kw"][a:b]) * DELTA_T)
        dis = float(np.sum(res["p_dis_kw"][a:b]) * DELTA_T)
        ws.cell(row=2 + i, column=2, value=chg)
        ws.cell(row=2 + i, column=3, value=dis)
    ws.cell(row=8, column=2, value=float(E_INIT))
    ws.cell(row=8, column=3, value=float(res["e_bat_kwh"][-1]))

    wb.save(out_path)
    print(f"[SUCCESS] Q1 results saved to: {out_path}")
    return out_path


def export_result(file_name, data_dict):
    """
    Writes generated data arrays to results/ (data/raw/ is read-only).
    If the target file is locked (open in Excel), falls back to a copy
    with a `_generated` suffix instead of crashing.
    """
    _ensure_dir(RESULTS_DIR)
    target_path = os.path.join(RESULTS_DIR, file_name)
    df = pd.DataFrame(data_dict)
    try:
        df.to_excel(target_path, index=False)
        print(f"[SUCCESS] Formatted energy outputs saved to: {target_path}")
    except PermissionError:
        base, ext = os.path.splitext(file_name)
        fallback = os.path.join(RESULTS_DIR, f"{base}_generated{ext}")
        df.to_excel(fallback, index=False)
        print(f"[WARNING] {file_name} is open in Excel; results saved to: {fallback}")