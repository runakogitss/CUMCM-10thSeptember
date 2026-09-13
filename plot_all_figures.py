#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
CUMCM 2026 论文配图一键批量渲染总控系统 (plot_all_figures.py)
功能:
  顺序调用 scripts/ 目录下的 4 个模块绘图脚本，在 figures/ 目录下生成标准化
  命名 (q1_fig1 ~ q4_fig1) 的 600 DPI 论文插图。
================================================================================
"""

import os
import sys
import time
import subprocess
from pathlib import Path

# 锁定工程根目录
PROJECT_ROOT = Path(__file__).resolve().parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
FIGURES_DIR = PROJECT_ROOT / "figures"
os.makedirs(FIGURES_DIR, exist_ok=True)

# 任务执行清单 (严格对齐 q1 ~ q4 题号顺序)
TASKS = [
    ("问题一 典型日阶梯时序、储能吞吐与相图", SCRIPTS_DIR / "plot_q1_figures.py"),
    ("问题二 鲁棒敏感性 U 型曲线与策略对比", SCRIPTS_DIR / "plot_q2_figures.py"),
    ("问题三 MPC 闭环滚动调整与偏差分解时序", SCRIPTS_DIR / "plot_q3_figures.py"),
    ("问题四 动态电价微网套利响应与机制全景", SCRIPTS_DIR / "plot_q4_figures.py"),
]

EXPECTED_OUTPUTS = [
    ("问题一 图 1 (购电阶梯时序)", FIGURES_DIR / "q1_fig1_diurnal_grid_procurement.png"),
    ("问题一 图 2 (储能双向吞吐)", FIGURES_DIR / "q1_fig2_bess_energy_balance.png"),
    ("问题一 图 3 (极坐标与ECDF)", FIGURES_DIR / "q1_fig3_polar_cumulative_spectrum.png"),
    ("问题二 图 1 (鲁棒敏感性U型)", FIGURES_DIR / "q2_fig1_robust_sensitivity.png"),
    ("问题三 图 1 (MPC日内滚动)", FIGURES_DIR / "q3_fig1_mpc_rolling_adjustment.png"),
    ("问题四 图 1 (动态电价响应)", FIGURES_DIR / "q4_fig1_dynamic_price_response.png"),
]


def main():
    total_start = time.time()
    print("\n" + "=" * 78)
    print(" CUMCM 2026 论文核心配图批量渲染系统 ")
    print("=" * 78)

    success_count = 0
    for idx, (desc, script_path) in enumerate(TASKS, 1):
        if not script_path.exists():
            alt_path = SCRIPTS_DIR / "plot_q2_sensitive.py"
            if "问题二" in desc and alt_path.exists():
                script_path = alt_path
            else:
                print(f"\n[{idx}/4] [警告 WARN] 缺失脚本: {script_path}，已跳过。")
                continue

        print(f"\n[{idx}/4] 正在渲染: {desc} ...")
        t0 = time.time()
        res = subprocess.run([sys.executable, str(script_path)], cwd=str(PROJECT_ROOT))
        t1 = time.time()

        if res.returncode == 0:
            print(f"      [完成 OK] 耗时: {t1 - t0:.2f} 秒")
            success_count += 1
        else:
            print(f"      [失败 FAIL] {script_path.name} 执行异常，退出码: {res.returncode}")

    total_time = time.time() - total_start
    print("\n" + "=" * 78)
    print(f" 渲染任务执行完毕！成功完成: {success_count}/{len(TASKS)} | 总耗时: {total_time:.2f} 秒")
    print(" 最终交付规范化配图清单核验:")
    
    all_ready = True
    for label, fpath in EXPECTED_OUTPUTS:
        status = "[已就绪 OK]" if fpath.exists() else "[缺失 MISS]"
        print(f"  {status} {label:<24} -> {fpath.name}")
        if not fpath.exists():
            all_ready = False

    print("=" * 78 + "\n")


if __name__ == "__main__":
    main()