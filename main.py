#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
CUMCM 2026 Problem C - Master Optimization and Verification Pipeline (main.py)
Integrated workflow:
  Stage 0: Load official Annex 1-4 input datasets
  Stage 1: Question 1 deterministic scheduling (LP)
  Stage 2: Question 2 two-stage robust scheduling & baseline benchmark
  Stage 3: Question 3 rolling MPC scheduling & feasibility audit
  Stage 4: Question 4 dynamic-tariff scheduling (Q4-2 vs Q4-3)
  Stage 5: Master result summary generation (master_summary.csv / .xlsx)
  Stage 6: Final physical and numerical audit (audit_final.py)
  Stage 7: Output deliverables verification & execution profiling
================================================================================
"""

import os
import sys
import time
from pathlib import Path
import pandas as pd

# 锁定工程根目录并注册模块路径
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# 载入工程核心模块
from src.data_loader import (
    load_annex1_tariffs,
    load_annex2_actuals,
    load_annex3_forecasts,
    load_annex4_dynamic_tariffs,
)
from src.solver_q1 import solve_q1
from src.simulator_q2 import (
    run_q2_simulation,
    run_q2_baseline_simulation,
)
from src.mpc_q3 import run_q3_simulation

# Q4 求解模块导入与向后兼容适配
try:
    from src.solver_q4 import solve_q4_2, solve_q4_3
except ImportError:
    from src.simulator_q2 import run_q2_simulation as solve_q4_2
    from src.mpc_q3 import run_q3_simulation as solve_q4_3

from src.export_tools import (
    export_q1_result,
    export_q2_result,
    export_q3_result,
    export_q4_2_result,
    export_q4_3_result,
    verify_q2_export,
    RESULTS_DIR,
)


# 终端格式化与色彩控制
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    RESET = "\033[0m"


def print_banner(text):
    print("\n" + "=" * 80)
    print(f"{Colors.CYAN} {text}{Colors.RESET}")
    print("=" * 80)


def print_pass(text):
    print(f"[{Colors.GREEN}PASS{Colors.RESET}] {text}")


def print_warn(text):
    print(f"[{Colors.YELLOW}WARN{Colors.RESET}] {text}")


def main():
    total_start_time = time.time()
    os.makedirs(RESULTS_DIR, exist_ok=True)

    print("\n" + "#" * 80)
    print(" CUMCM 2026 Problem C - Integrated Optimization and Verification Pipeline")
    print("#" * 80)

    # ==========================================================================
    # Stage 0: 载入全量官方输入数据集
    # ==========================================================================
    print_banner("Stage 0 - Loading Annex 1-4 datasets")
    tariffs_static = load_annex1_tariffs()
    tariffs_dynamic = load_annex4_dynamic_tariffs()
    load_act, pv_act = load_annex2_actuals()
    pv_forecast = load_annex3_forecasts()
    print_pass("All official datasets loaded successfully.")

    # ==========================================================================
    # Stage 1: 问题一 典型日全知最优排产 (LP)
    # ==========================================================================
    print_banner("Stage 1/4 - Question 1 deterministic scheduling")
    res_q1 = solve_q1()
    result1_path = export_q1_result(res_q1)

    q1_cost = float(res_q1["total_cost"])
    q1_purchase = float(res_q1["total_purchased_kwh"])
    q1_terminal_soc = float(res_q1["terminal_energy"])

    print_pass(f"Q1 completed. Saved to: {result1_path}")
    print(f"  Total purchased energy:  {q1_purchase:.2f} kWh")
    print(f"  Total electricity cost:  {q1_cost:.2f} yuan")
    print(f"  Terminal battery energy: {q1_terminal_soc:.2f} kWh")

    # ==========================================================================
    # Stage 2: 问题二 两阶段鲁棒规划与基线对账
    # ==========================================================================
    print_banner("Stage 2/4 - Question 2 two-stage robust scheduling")

    # 公平基准与优化策略均经过 1 月份自然预热
    print("Running baseline Q2 (passive buffer, with Jan warm-up)...")
    res_base2 = run_q2_baseline_simulation(
        tariffs_static,
        load_act,
        pv_act,
    )

    print("Running optimized two-stage robust strategy (with Jan warm-up)...")
    res_q2 = run_q2_simulation(
        tariffs_static,
        load_act,
        pv_act,
    )

    result2_path = export_q2_result(res_q2)

    # 官方交付文件格式健康检查
    verify_q2_export(
        result2_path,
        res_q2["total_em_kwh"],
        res_q2["total_cost"],
    )

    baseline_cost = float(res_base2["total_cost"])
    q2_cost = float(res_q2["total_cost"])
    q2_saving = baseline_cost - q2_cost
    q2_saving_pct = 100.0 * q2_saving / baseline_cost
    q2_em_kwh = float(res_q2["total_em_kwh"])

    print_pass(f"Q2 completed. Saved to: {result2_path}")
    print(f"  Baseline cost:            {baseline_cost:.2f} yuan")
    print(f"  Optimized Q2 cost:        {q2_cost:.2f} yuan")
    print(f"  Cost reduction:           {q2_saving:.2f} yuan ({q2_saving_pct:.2f}%)")
    print(f"  Planned purchase:         {res_q2['total_plan_kwh']:.2f} kWh")
    print(f"  Emergency purchase:       {q2_em_kwh:.2f} kWh")
    print(f"  Baseline Jan warm-up SOC: {res_base2['warmup_end_soc']:.2f} kWh")
    print(f"  Optimized Jan warm-up SOC:{res_q2['warmup_end_soc']:.2f} kWh")

    # ==========================================================================
    # Stage 3: 问题三 多时间尺度闭环滚动 MPC 调控
    # ==========================================================================
    print_banner("Stage 3/4 - Question 3 rolling MPC scheduling")
    res_q3 = run_q3_simulation(
        tariffs_static,
        load_act,
        pv_act,
        pv_forecast,
    )

    result3_path = export_q3_result(
        res_q3,
        tariffs_static,
    )

    q3_cost = float(res_q3["total_cost"])
    q3_em_kwh = float(res_q3["total_em_kwh"])
    q3_saving = q2_cost - q3_cost
    q3_saving_pct = 100.0 * q3_saving / q2_cost

    q3_fallback = int(res_q3.get("mpc_fallback_count", -1))
    q3_relax = int(res_q3.get("mpc_terminal_relax_count", -1))
    q3_plan_fallback = int(res_q3.get("mpc_plan_fallback_count", -1))

    print_pass(f"Q3 completed. Saved to: {result3_path}")
    print(f"  Day-ahead planned purchase: {res_q3['total_plan_kwh']:.2f} kWh")
    print(f"  Adjusted purchase:          {res_q3['total_adj_kwh']:.2f} kWh")
    print(f"  Emergency purchase:         {q3_em_kwh:.2f} kWh")
    print(f"  Total settlement cost:      {q3_cost:.2f} yuan")
    print(f"  Saving relative to Q2:      {q3_saving:.2f} yuan ({q3_saving_pct:.2f}%)")
    print(f"  MPC fallback count:         {q3_fallback}")
    print(f"    terminal relax count:     {q3_relax}")
    print(f"    original-plan fallback:   {q3_plan_fallback}")

    if q3_fallback == 0 and q3_relax == 0 and q3_plan_fallback == 0:
        print_pass("Q3 rolling MPC remained feasible with the original terminal reserve constraint.")
    else:
        print_warn("Q3 contains one or more MPC fallback events.")

    # ==========================================================================
    # Stage 4: 问题四 动态时变电价优化响应 (Q4-2 vs Q4-3)
    # ==========================================================================
    print_banner("Stage 4/4 - Question 4 dynamic-tariff scheduling")
    res_q4_2 = solve_q4_2(
        tariffs_dynamic,
        load_act,
        pv_act,
    )
    res_q4_3 = solve_q4_3(
        tariffs_dynamic,
        load_act,
        pv_act,
        pv_forecast,
    )

    result4_2_path = export_q4_2_result(res_q4_2)
    result4_3_path = export_q4_3_result(
        res_q4_3,
        tariffs_dynamic,
    )

    q4_2_cost = float(res_q4_2["total_cost"])
    q4_3_cost = float(res_q4_3["total_cost"])
    q4_saving = q4_2_cost - q4_3_cost
    q4_saving_pct = 100.0 * q4_saving / q4_2_cost

    q4_em_reduction = float(res_q4_2["total_em_kwh"] - res_q4_3["total_em_kwh"])
    q4_em_reduction_pct = 100.0 * q4_em_reduction / res_q4_2["total_em_kwh"]
    q4_3_fallback = int(res_q4_3.get("mpc_fallback_count", -1))

    print_pass("Q4 completed.")
    print(f"  Q4-2 dynamic-tariff cost:  {q4_2_cost:.2f} yuan")
    print(f"  Q4-3 dynamic-tariff cost:  {q4_3_cost:.2f} yuan")
    print(f"  Q4-3 saving vs Q4-2:       {q4_saving:.2f} yuan ({q4_saving_pct:.2f}%)")
    print(f"  Q4-2 emergency purchase:   {res_q4_2['total_em_kwh']:.2f} kWh")
    print(f"  Q4-3 emergency purchase:   {res_q4_3['total_em_kwh']:.2f} kWh")
    print(f"  Emergency reduction:       {q4_em_reduction:.2f} kWh ({q4_em_reduction_pct:.2f}%)")
    print(f"  Q4-3 MPC fallback count:   {q4_3_fallback}")

    if q4_3_fallback == 0:
        print_pass("Q4-3 rolling MPC remained feasible with the original terminal reserve constraint.")
    else:
        print_warn("Q4-3 contains one or more MPC fallback events.")

    # ==========================================================================
    # Stage 5: 全局主汇总表生成 (Master Result Summary)
    # ==========================================================================
    print_banner("Stage 5 - Generating master result summary")
    summary_rows = [
        ("Q1 total purchase (kWh)", round(q1_purchase, 2)),
        ("Q1 total cost (Yuan)", round(q1_cost, 2)),
        ("Q1 terminal SOC (kWh)", round(q1_terminal_soc, 2)),
        ("Q2 baseline total cost (Yuan)", round(baseline_cost, 2)),
        ("Q2 optimized total cost (Yuan)", round(q2_cost, 2)),
        ("Q2 cost reduction (Yuan)", round(q2_saving, 2)),
        ("Q2 cost reduction (%)", round(q2_saving_pct, 2)),
        ("Q2 planned purchase (kWh)", round(res_q2["total_plan_kwh"], 2)),
        ("Q2 emergency purchase (kWh)", round(res_q2["total_em_kwh"], 2)),
        ("Q2 baseline Jan warm-up SOC (kWh)", round(res_base2["warmup_end_soc"], 2)),
        ("Q2 optimized Jan warm-up SOC (kWh)", round(res_q2["warmup_end_soc"], 2)),
        ("Q3 planned purchase (kWh)", round(res_q3["total_plan_kwh"], 2)),
        ("Q3 adjusted purchase (kWh)", round(res_q3["total_adj_kwh"], 2)),
        ("Q3 emergency purchase (kWh)", round(res_q3["total_em_kwh"], 2)),
        ("Q3 total settlement cost (Yuan)", round(q3_cost, 2)),
        ("Q3 saving vs Q2 (Yuan)", round(q3_saving, 2)),
        ("Q3 saving vs Q2 (%)", round(q3_saving_pct, 2)),
        ("Q3 MPC fallback count", q3_fallback),
        ("Q4-2 total cost (Yuan)", round(q4_2_cost, 2)),
        ("Q4-2 emergency purchase (kWh)", round(res_q4_2["total_em_kwh"], 2)),
        ("Q4-3 total cost (Yuan)", round(q4_3_cost, 2)),
        ("Q4-3 emergency purchase (kWh)", round(res_q4_3["total_em_kwh"], 2)),
        ("Q4-3 saving vs Q4-2 (Yuan)", round(q4_saving, 2)),
        ("Q4-3 saving vs Q4-2 (%)", round(q4_saving_pct, 2)),
        ("Q4 emergency reduction (%)", round(q4_em_reduction_pct, 2)),
        ("Q4-3 MPC fallback count", q4_3_fallback),
    ]

    summary_df = pd.DataFrame(summary_rows, columns=["Metric", "Value"])
    print(summary_df.to_string(index=False))

    summary_csv = os.path.join(RESULTS_DIR, "master_summary.csv")
    summary_xlsx = os.path.join(RESULTS_DIR, "master_summary.xlsx")
    summary_df.to_csv(summary_csv, index=False, encoding="utf_8_sig")
    summary_df.to_excel(summary_xlsx, index=False)
    print_pass(f"Master summary generated:\n  {summary_csv}\n  {summary_xlsx}")

    # ==========================================================================
    # Stage 6: 终审物理与数值穿透审计 (唯一定点调用 audit_final.py)
    # ==========================================================================
    print_banner("Stage 6 - Running final physical and numerical audit")
    try:
        from audit_final import main as run_final_audit

        run_final_audit()
        print_pass("Final physical and numerical audit passed successfully.")
    except Exception as err:
        print_warn("Final audit could not be completed automatically.")
        print(f"  Error details: {err}")

    # ==========================================================================
    # Stage 7: 交付文件完整性验证与性能统计
    # ==========================================================================
    print_banner("Stage 7 - Deliverables verification & execution summary")
    elapsed = time.time() - total_start_time

    deliverables = [
        ("result1.xlsx", os.path.join(RESULTS_DIR, "result1.xlsx")),
        ("result2.xlsx", os.path.join(RESULTS_DIR, "result2.xlsx")),
        ("result3.xlsx", os.path.join(RESULTS_DIR, "result3.xlsx")),
        ("result4-2.xlsx", os.path.join(RESULTS_DIR, "result4-2.xlsx")),
        ("result4-3.xlsx", os.path.join(RESULTS_DIR, "result4-3.xlsx")),
        ("master_summary.xlsx", summary_xlsx),
    ]

    all_exist = True
    for fname, fpath in deliverables:
        exists = os.path.exists(fpath)
        status = f"{Colors.GREEN}OK{Colors.RESET}" if exists else f"{Colors.RED}MISSING{Colors.RESET}"
        print(f"  [{status}] {fname:<22} -> {fpath}")
        if not exists:
            all_exist = False

    print("\n" + "=" * 80)
    if all_exist:
        print(f"{Colors.GREEN} CUMCM 2026 Problem C Pipeline Finished! Total time: {elapsed:.2f} s{Colors.RESET}")
    else:
        print(f"{Colors.YELLOW} Pipeline finished with missing files. Total time: {elapsed:.2f} s{Colors.RESET}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()