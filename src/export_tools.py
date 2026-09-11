import os
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from openpyxl import load_workbook

from src.config import DELTA_T, E_INIT, STEPS_PER_DAY

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "Annex5_Templates")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")

# 4-hour aggregation windows: (start_step, end_step) exclusive end.
FOUR_HOUR_WINDOWS = [
    (0, 24), (24, 48), (48, 72), (72, 96), (96, 120), (120, 144),
]
FOUR_HOUR_LABELS = [
    "0:00-4:00", "4:00-8:00", "8:00-12:00",
    "12:00-16:00", "16:00-20:00", "20:00-24:00",
]

Q2_START_DATE = datetime(2025, 2, 1)


def _step_time_label(step):
    hours, minutes = divmod(step * 10, 60)
    return f"{hours}:{minutes:02d}"


def _contiguous_runs(mask):
    runs = []
    start = None
    for i, flag in enumerate(mask):
        if flag and start is None:
            start = i
        elif not flag and start is not None:
            runs.append((start, i - 1))
            start = None
    if start is not None:
        runs.append((start, len(mask) - 1))
    return runs


def _ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def export_q1_result(res):
    """
    Populates the blank Annex 5 result1 template and saves to results/result1.xlsx.
    Never overwrites data/raw templates.
    """
    template_path = os.path.join(TEMPLATES_DIR, "result1.xlsx")
    out_path = os.path.join(RESULTS_DIR, "result1.xlsx")
    _ensure_dir(RESULTS_DIR)

    wb = load_workbook(template_path)

    ws1 = wb["计划购电量"]
    for t in range(len(res["p_grid_kw"])):
        ws1.cell(row=2 + t, column=2, value=float(round(res["p_grid_kw"][t] * DELTA_T, 4)))

    ws2 = wb["充放电量"]
    for i, (a, b) in enumerate(FOUR_HOUR_WINDOWS):
        chg = float(np.sum(res["p_chg_kw"][a:b]) * DELTA_T)
        dis = float(np.sum(res["p_dis_kw"][a:b]) * DELTA_T)
        ws2.cell(row=2 + i, column=2, value=float(round(chg, 4)))
        ws2.cell(row=2 + i, column=3, value=float(round(dis, 4)))

    for r in range(1, ws2.max_row + 1):
        for c in range(1, ws2.max_column + 1):
            val = str(ws2.cell(row=r, column=c).value).strip()
            if val in ["0:00", "0:00:00"]:
                ws2.cell(row=r, column=c + 1, value=6000.0)
            elif val in ["24:00", "24:00:00", "0:00+1"]:
                ws2.cell(row=r, column=c + 1, value=6000.0)

    wb.save(out_path)
    print(f"[SUCCESS] Q1 deliverables correctly mapped to: {out_path}")

    flat_df = pd.DataFrame({
        "P_grid_kWh": np.asarray(res["p_grid_kw"]) * DELTA_T,
        "P_chg_kWh": np.asarray(res["p_chg_kw"]) * DELTA_T,
        "P_dis_kWh": np.asarray(res["p_dis_kw"]) * DELTA_T,
        "P_curt_kWh": np.asarray(res["p_curt_kw"]) * DELTA_T,
        "E_bat_kWh": np.asarray(res["e_bat_kwh"]),
    })
    csv_path = os.path.join(RESULTS_DIR, "result1.csv")
    flat_df.to_csv(csv_path, index=False)
    print(f"[SUCCESS] Q1 long-format series saved to: {csv_path}")
    return out_path


def _fill_plan_sheet(ws, num_days, steps, p_series, daily_energy, daily_cost):
    """Fills a 计划购电量-style sheet (date + 144 kWh steps + daily totals)."""
    for d in range(num_days):
        row = 2 + d
        day = p_series[d * steps:(d + 1) * steps]
        for t in range(steps):
            ws.cell(row=row, column=2 + t, value=float(round(day[t], 4)))
        ws.cell(row=row, column=146, value=float(round(float(daily_energy[d]), 4)))
        ws.cell(row=row, column=147, value=float(round(float(daily_cost[d]), 4)))


def _fill_charge_discharge_sheet(ws, num_days, steps, p_chg, p_dis, e_bat, e_day_start):
    """Fills a 充放电量 sheet: 6 four-hour blocks per day with 0:00/24:00 SOC."""
    if ws.max_row >= 2:
        ws.delete_rows(2, ws.max_row)
    row = 2
    for d in range(num_days):
        date_str = (Q2_START_DATE + timedelta(days=d)).strftime("%Y-%m-%d")
        day_chg = p_chg[d * steps:(d + 1) * steps]
        day_dis = p_dis[d * steps:(d + 1) * steps]
        e_end = float(e_bat[(d + 1) * steps - 1])
        for i, (a, b) in enumerate(FOUR_HOUR_WINDOWS):
            r = row + i
            ws.cell(row=r, column=1, value=date_str)
            ws.cell(row=r, column=2, value=FOUR_HOUR_LABELS[i])
            ws.cell(row=r, column=3, value=float(round(float(np.sum(day_chg[a:b])), 4)))
            ws.cell(row=r, column=4, value=float(round(float(np.sum(day_dis[a:b])), 4)))
            if i == 0:
                ws.cell(row=r, column=5, value="00:00:00")
                ws.cell(row=r, column=6, value=float(round(float(e_day_start[d]), 4)))
            elif i == 1:
                ws.cell(row=r, column=5, value="24:00")
                ws.cell(row=r, column=6, value=float(round(e_end, 4)))
        row += len(FOUR_HOUR_WINDOWS)


def _fill_emergency_sheet(ws, num_days, steps, p_em):
    """Fills a 紧急购电量 event ledger (only actual events, 3 template columns)."""
    if ws.max_row >= 2:
        ws.delete_rows(2, ws.max_row)
    row = 2
    for d in range(num_days):
        date_str = (Q2_START_DATE + timedelta(days=d)).strftime("%Y-%m-%d")
        day_em = p_em[d * steps:(d + 1) * steps]
        for a, b in _contiguous_runs(day_em > 1e-9):
            ws.cell(row=row, column=1, value=date_str)
            ws.cell(row=row, column=2,
                     value=f"{_step_time_label(a)}-{_step_time_label(b + 1)}")
            ws.cell(row=row, column=3,
                     value=float(round(float(np.sum(day_em[a:b + 1])), 4)))
            row += 1


def export_q2_result(res):
    """
    Populates the blank Annex 5 result2 template and saves to results/Q2_optimized.xlsx
    plus a flat Q2_optimized.csv.

    Sheet 1 '计划购电量': per 10-min planned purchase energy per day plus the
    whole-day planned energy and planned purchase cost.
    Sheet 2 '充放电量': 4-hour aggregated charge/discharge energy and the
    battery state at 00:00 and 24:00 for every day.
    Sheet 3 '紧急购电量': event ledger of every emergency purchase.
    """
    template_path = os.path.join(TEMPLATES_DIR, "result2.xlsx")
    out_path = os.path.join(RESULTS_DIR, "Q2_optimized.xlsx")
    _ensure_dir(RESULTS_DIR)

    wb = load_workbook(template_path)

    num_days = int(res["num_days"])
    steps = STEPS_PER_DAY
    p_plan = res["p_plan_kwh"]
    p_em = res["p_em_kwh"]
    p_chg = res["p_chg_kwh"]
    p_dis = res["p_dis_kwh"]
    e_bat = res["e_bat_kwh"]
    e_day_start = res["e_day_start"]

    _fill_plan_sheet(wb["计划购电量"], num_days, steps, p_plan,
                     res["daily_plan_energy"], res["daily_planned_cost"])
    _fill_charge_discharge_sheet(wb["充放电量"], num_days, steps,
                                 p_chg, p_dis, e_bat, e_day_start)
    _fill_emergency_sheet(wb["紧急购电量"], num_days, steps, p_em)

    wb.save(out_path)
    print(f"[SUCCESS] Q2 optimized deliverables correctly mapped to: {out_path}")

    long_df = pd.DataFrame({
        "P_plan_kWh": p_plan,
        "P_em_kWh": p_em,
        "E_bat_kWh": e_bat,
    })
    csv_path = os.path.join(RESULTS_DIR, "Q2_optimized.csv")
    long_df.to_csv(csv_path, index=False)
    print(f"[SUCCESS] Q2 optimized long-format series saved to: {csv_path}")
    return out_path


def export_q4_2_result(res):
    """
    Populates the Annex 5 result4-2 template (same multi-sheet layout as
    result2) with the dynamic-tariff two-stage Q4-2 results.
    """
    template_path = os.path.join(TEMPLATES_DIR, "result4-2.xlsx")
    out_path = os.path.join(RESULTS_DIR, "result4-2.xlsx")
    _ensure_dir(RESULTS_DIR)

    wb = load_workbook(template_path)

    num_days = int(res["num_days"])
    steps = STEPS_PER_DAY
    p_plan = res["p_plan_kwh"]
    p_em = res["p_em_kwh"]
    p_chg = res["p_chg_kwh"]
    p_dis = res["p_dis_kwh"]
    e_bat = res["e_bat_kwh"]
    e_day_start = res["e_day_start"]

    _fill_plan_sheet(wb["计划购电量"], num_days, steps, p_plan,
                     res["daily_plan_energy"], res["daily_planned_cost"])
    _fill_charge_discharge_sheet(wb["充放电量"], num_days, steps,
                                 p_chg, p_dis, e_bat, e_day_start)
    _fill_emergency_sheet(wb["紧急购电量"], num_days, steps, p_em)

    wb.save(out_path)
    print(f"[SUCCESS] Q4-2 deliverables correctly mapped to: {out_path}")

    long_df = pd.DataFrame({
        "P_plan_kWh": p_plan,
        "P_em_kWh": p_em,
        "E_bat_kWh": e_bat,
    })
    csv_path = os.path.join(RESULTS_DIR, "result4-2.csv")
    long_df.to_csv(csv_path, index=False)
    print(f"[SUCCESS] Q4-2 long-format series saved to: {csv_path}")
    return out_path


def export_q4_3_result(res, tariffs_matrix):
    """
    Populates the Annex 5 result4-3 template (4 sheets) with the dynamic-tariff
    rolling MPC results: 计划购电量 (P_plan), 调整购电量 (P_adj), 充放电量 and
    紧急购电量. Also writes a flat result4-3.csv.
    """
    template_path = os.path.join(TEMPLATES_DIR, "result4-3.xlsx")
    out_path = os.path.join(RESULTS_DIR, "result4-3.xlsx")
    _ensure_dir(RESULTS_DIR)

    wb = load_workbook(template_path)

    num_days = int(res["num_days"])
    steps = STEPS_PER_DAY
    p_plan = res["p_plan_kwh"]
    p_adj = res["p_adj_kwh"]
    p_em = res["p_em_kwh"]
    p_chg = res["p_chg_kwh"]
    p_dis = res["p_dis_kwh"]
    e_bat = res["e_bat_kwh"]
    start_day = int(res["start_day"])

    e_day_start = np.zeros(num_days)
    daily_plan_energy = np.zeros(num_days)
    daily_plan_cost = np.zeros(num_days)
    daily_adj_energy = np.zeros(num_days)
    daily_adj_cost = np.zeros(num_days)
    for d in range(num_days):
        tariff_d = (tariffs_matrix[start_day + d]
                    if tariffs_matrix.ndim == 2 else tariffs_matrix)
        day_plan = p_plan[d * steps:(d + 1) * steps]
        day_adj = p_adj[d * steps:(d + 1) * steps]
        daily_plan_energy[d] = float(np.sum(day_plan))
        daily_adj_energy[d] = float(np.sum(day_adj))
        daily_plan_cost[d] = float(np.sum(tariff_d * day_plan))
        daily_adj_cost[d] = float(np.sum(tariff_d * day_adj))
        e_day_start[d] = float(E_INIT if d == 0 else e_bat[d * steps - 1])

    _fill_plan_sheet(wb["计划购电量"], num_days, steps, p_plan,
                     daily_plan_energy, daily_plan_cost)
    _fill_plan_sheet(wb["调整购电量"], num_days, steps, p_adj,
                     daily_adj_energy, daily_adj_cost)
    _fill_charge_discharge_sheet(wb["充放电量"], num_days, steps,
                                 p_chg, p_dis, e_bat, e_day_start)
    _fill_emergency_sheet(wb["紧急购电量"], num_days, steps, p_em)

    wb.save(out_path)
    print(f"[SUCCESS] Q4-3 deliverables correctly mapped to: {out_path}")

    long_df = pd.DataFrame({
        "P_plan_kWh": p_plan,
        "P_adj_kWh": p_adj,
        "P_em_kWh": p_em,
        "E_bat_kWh": e_bat,
    })
    csv_path = os.path.join(RESULTS_DIR, "result4-3.csv")
    long_df.to_csv(csv_path, index=False)
    print(f"[SUCCESS] Q4-3 long-format series saved to: {csv_path}")
    return out_path


def verify_q2_export(out_path, total_em_kwh=None, total_cost=None):
    """
    Automated health check on the exported result2 workbook against the
    official Annex 5 template requirements.
    """
    checks = []

    d1 = pd.read_excel(out_path, sheet_name="计划购电量", header=None)
    checks.append(("Sheet1: 334 data rows", d1.shape[0] - 1, 334))
    checks.append(("Sheet1: 147 cols", d1.shape[1], 147))
    checks.append(("Sheet1: NaT/NaN in data block",
                   int(d1.iloc[1:, 1:145].isna().sum().sum()), 0))

    d2 = pd.read_excel(out_path, sheet_name="充放电量", header=None)
    checks.append(("Sheet2: 2004 data rows", d2.shape[0] - 1, 2004))
    checks.append(("Sheet2: 6 cols", d2.shape[1], 6))
    checks.append(("Sheet2: NaT in Column A (日期)",
                   int(d2.iloc[1:, 0].isna().sum()), 0))

    d3 = pd.read_excel(out_path, sheet_name="紧急购电量", header=None)
    header_ok = [str(v) for v in d3.iloc[0, :3].tolist()] == ["日期", "购电时间段", "购电量"]
    checks.append(("Sheet3: 3-col header match", header_ok, True))
    placeholder = int((d3.iloc[1:, 0].isna() | d3.iloc[1:, 2].isna()).sum())
    checks.append(("Sheet3: NaN placeholder rows", placeholder, 0))
    em_sum = float(d3.iloc[1:, 2].astype(float).sum())
    if total_em_kwh is not None:
        checks.append(("Sheet3: total emergency kWh",
                       round(em_sum, 2), round(float(total_em_kwh), 2)))
    checks.append(("Sheet3: event rows", int(d3.iloc[1:, 2].notna().sum()), None))

    if total_cost is not None:
        checks.append(("Total Q2 cost (Yuan)", round(float(total_cost), 2), None))

    all_pass = True
    print("\n=== Q2 Export Health Check ===")
    for name, got, want in checks:
        ok = (want is None) or (got == want)
        all_pass &= ok
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got={got} expect={want}")
    print(f"  >>> {'ALL CHECKS PASSED' if all_pass else 'SOME CHECKS FAILED'} <<<")
    return all_pass


def export_result(file_name, data_dict):
    """
    Writes generated data arrays to results/ in both xlsx and csv formats
    (data/raw/ is read-only). If the target file is locked (open in Excel),
    falls back to a copy with a `_generated` suffix instead of crashing.
    """
    _ensure_dir(RESULTS_DIR)
    base, ext = os.path.splitext(file_name)
    df = pd.DataFrame(data_dict)
    try:
        df.to_excel(os.path.join(RESULTS_DIR, file_name), index=False)
        print(f"[SUCCESS] Formatted energy outputs saved to: {os.path.join(RESULTS_DIR, file_name)}")
    except PermissionError:
        fallback_xlsx = os.path.join(RESULTS_DIR, f"{base}_generated.xlsx")
        df.to_excel(fallback_xlsx, index=False)
        print(f"[WARNING] {file_name} is open in Excel; results saved to: {fallback_xlsx}")

    try:
        csv_path = os.path.join(RESULTS_DIR, f"{base}.csv")
        df.to_csv(csv_path, index=False)
        print(f"[SUCCESS] Formatted energy outputs saved to: {csv_path}")
    except PermissionError:
        fallback_csv = os.path.join(RESULTS_DIR, f"{base}_generated.csv")
        df.to_csv(fallback_csv, index=False)
        print(f"[WARNING] {file_name} csv is open; results saved to: {fallback_csv}")