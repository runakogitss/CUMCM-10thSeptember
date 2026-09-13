#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
全国大学生数学建模竞赛 (CUMCM) 论文核心学术级配图脚本 (问题 2 敏感性分析与策略对比)
输出图表: figures/q2_fig1_robust_sensitivity.png
内容涵盖: (a) 鲁棒安全系数 z 参数敏感性分析 (非对称报童 U 型成本权衡曲线与极值标定)
          (b) 规则基线与两阶段鲁棒策略全周期经济性对比
标准规范: GB 3100~3102-1993 量和单位规范、宋体+Times New Roman混排、600 DPI 分辨率
================================================================================
"""

import os
import sys
import subprocess
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

# ------------------------------------------------------------------------------
# 动态定位工程根目录与输入输出路径
# ------------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
FIGURES_DIR = os.path.join(PROJECT_ROOT, "figures")
os.makedirs(FIGURES_DIR, exist_ok=True)

CSV_PATH = os.path.join(RESULTS_DIR, "q2_z_sensitivity.csv")
OUTPUT_PATH = os.path.join(FIGURES_DIR, "q2_fig1_robust_sensitivity.png")

# ------------------------------------------------------------------------------
# 自动自愈守护机制：若数据文件缺失，自动触发生成脚本
# ------------------------------------------------------------------------------
if not os.path.exists(CSV_PATH):
    print("[提示] 检测到 results/q2_z_sensitivity.csv 缺失，正在自动调用 q2_sensitive.py 重建数据...")
    gen_script = PROJECT_ROOT / "q2_sensitive.py"
    if gen_script.exists():
        subprocess.run([sys.executable, str(gen_script)], cwd=str(PROJECT_ROOT), check=True)
    else:
        raise FileNotFoundError(f"未在根目录找到敏感性计算脚本: {gen_script}")

# ------------------------------------------------------------------------------
# 1. 全局学术排版与字体配置
# ------------------------------------------------------------------------------
plt.rcParams['font.sans-serif'] = ['SimSun', 'Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['mathtext.fontset'] = 'stix'

plt.rcParams['font.size'] = 10.5
plt.rcParams['axes.titlesize'] = 10.5
plt.rcParams['axes.labelsize'] = 10.5
plt.rcParams['xtick.labelsize'] = 9.0
plt.rcParams['ytick.labelsize'] = 9.0
plt.rcParams['legend.fontsize'] = 8.6
plt.rcParams['figure.titlesize'] = 11.5

plt.rcParams['figure.facecolor'] = '#FFFFFF'
plt.rcParams['axes.facecolor'] = '#FFFFFF'
plt.rcParams['axes.edgecolor'] = '#000000'
plt.rcParams['axes.linewidth'] = 1.2
plt.rcParams['grid.linewidth'] = 0.5
plt.rcParams['grid.alpha'] = 0.35
plt.rcParams['grid.color'] = '#7F7F7F'
plt.rcParams['xtick.direction'] = 'in'
plt.rcParams['ytick.direction'] = 'in'
plt.rcParams['xtick.major.size'] = 4.5
plt.rcParams['ytick.major.size'] = 4.5

def italic_num(val, pos):
    if abs(val - int(val)) < 1e-5:
        return f"$\\mathit{{{int(val)}}}$"
    return f"$\\mathit{{{val:.1f}}}$"

num_fmt = FuncFormatter(italic_num)

# 低饱和度科研配色体系
COLOR_PLAN = "#3B6E8C"        # 计划购电成本：沉稳灰蓝
COLOR_EMERGENCY = "#B5533C"   # 紧急购电成本：低饱和陶土红
COLOR_TOTAL = "#2F4F4F"       # 总购电成本：深海板岩青灰
COLOR_BEST = "#C87D28"        # 最优极值点：暗金/暖赭色
COLOR_BASELINE = "#64748B"    # 规则基准方案：中性石板灰
COLOR_ROBUST = "#2F4F4F"      # 两阶段鲁棒策略：沉稳板岩深灰

# ------------------------------------------------------------------------------
# 2. 真实敏感性实验数据读取与基准指标
# ------------------------------------------------------------------------------
df = pd.read_csv(CSV_PATH)
z = df["z"].to_numpy()
plan_cost = df["planned_cost_yuan"].to_numpy() / 1e4
emergency_cost = df["emergency_cost_yuan"].to_numpy() / 1e4
total_cost = df["total_cost_yuan"].to_numpy() / 1e4

baseline_cost = 18832047.46 / 1e4
robust_cost = 16085410.43 / 1e4
saving_rate = (baseline_cost - robust_cost) / baseline_cost * 100

# ------------------------------------------------------------------------------
# 3. 核心画布绘制
# ------------------------------------------------------------------------------
fig, (ax1, ax2) = plt.subplots(
    1, 2,
    figsize=(11.6, 4.6),
    dpi=600,
    gridspec_kw={"width_ratios": [1.45, 0.95]}
)

# (a) 鲁棒安全系数 z 参数敏感性分析
ax1.plot(
    z, plan_cost,
    marker="o", color=COLOR_PLAN, linewidth=1.8, markersize=5.5,
    label="计划购电成本"
)
ax1.plot(
    z, emergency_cost,
    marker="s", color=COLOR_EMERGENCY, linewidth=1.8, markersize=5.5,
    label="紧急购电成本"
)
ax1.plot(
    z, total_cost,
    marker="D", color=COLOR_TOTAL, linewidth=2.2, markersize=6.0,
    label="总购电成本"
)

# 最优点标定
best_idx = np.argmin(total_cost)
best_z = z[best_idx]
best_cost = total_cost[best_idx]

ax1.scatter(
    best_z, best_cost,
    color=COLOR_BEST, edgecolors='#000000', s=70, zorder=5, lw=1.1
)
ax1.axvline(
    best_z,
    color='#555555', linestyle="--", linewidth=1.1, alpha=0.75, zorder=2
)

ax1.annotate(
    f"最低总成本\n$z = \\mathit{{{best_z:.3f}}}$\n$\\mathit{{{best_cost:.2f}}}$ 万元",
    xy=(best_z, best_cost),
    xytext=(0.71, 2080),
    arrowprops=dict(
        arrowstyle="->",
        color='#333333',
        linewidth=1.0,
        shrinkB=4
    ),
    fontsize=8.8,
    ha="center",
    va="center",
    zorder=6
)

ax1.set_xlabel("鲁棒安全系数 $z$", fontweight='bold', labelpad=6)
ax1.set_ylabel("全年购电成本 / 万元", fontweight='bold', labelpad=6)
ax1.set_title("(a) 鲁棒安全系数敏感性分析", loc="left", fontweight="bold", pad=10)

ax1.set_xticks(z)
ax1.set_xticklabels([f"$\\mathit{{{val:.3f}}}$" for val in z])
ax1.set_ylim(-80, 2550)
ax1.yaxis.set_major_formatter(num_fmt)
ax1.grid(True, linestyle=":", alpha=0.45)
ax1.legend(frameon=False, loc="upper right", fontsize=8.6)

# (b) 不同购电策略成本比较
methods = ["规则基线", "两阶段鲁棒策略"]
costs = [baseline_cost, robust_cost]

bars = ax2.bar(
    methods, costs,
    width=0.48,
    color=[COLOR_BASELINE, COLOR_ROBUST],
    edgecolor='#000000',
    lw=1.0
)

for bar, value in zip(bars, costs):
    ax2.text(
        bar.get_x() + bar.get_width() / 2.0,
        value + 35,
        f"$\\mathit{{{value:.2f}}}$",
        ha="center",
        va="bottom",
        fontsize=9.2,
        fontweight="bold"
    )

ax2.annotate(
    f"降低 $\\mathit{{{saving_rate:.2f}\\%}}$",
    xy=(0.80, robust_cost),
    xytext=(0.50, 1830),
    arrowprops=dict(
        arrowstyle="->",
        color='#333333',
        linewidth=1.0,
        shrinkB=4
    ),
    fontsize=9.2,
    ha="center",
    va="center",
    zorder=6
)

ax2.set_ylabel("全年总购电成本 / 万元", fontweight='bold', labelpad=6)
ax2.set_title("(b) 不同购电策略成本比较", loc="left", fontweight="bold", pad=10)
ax2.set_ylim(0, 2250)
ax2.yaxis.set_major_formatter(num_fmt)
ax2.grid(axis="y", linestyle=":", alpha=0.45)

# ------------------------------------------------------------------------------
# 4. 全局标题与导出
# ------------------------------------------------------------------------------
fig.suptitle(
    "问题二鲁棒参数敏感性与购电策略经济性比较",
    fontsize=11.5,
    fontweight="bold",
    y=0.98
)

fig.subplots_adjust(top=0.88, bottom=0.13, left=0.08, right=0.96, wspace=0.26)
plt.savefig(OUTPUT_PATH, dpi=600)
plt.close()

print(f"[通过 PASS] 问题二 图 1 已成功生成: {OUTPUT_PATH}")