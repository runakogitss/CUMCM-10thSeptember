#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
全国大学生数学建模竞赛 (CUMCM) 论文核心学术级配图脚本 (问题 4 动态电价机制响应)
输出图表: figures/q4_fig1_dynamic_price_response.png
内容涵盖: (a) 全年最高电价代表日 (2025-07-03) 动态电价与储能削峰填谷响应
          (b) 动态电价环境下 Q4-2 (两阶段鲁棒) 与 Q4-3 (滚动优化) 经济性与避险全景
标准规范: GB 3100~3102-1993 量和单位规范、宋体+Times New Roman混排、60 DPI 分辨率
================================================================================
"""

import os
import sys
from pathlib import Path
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

# ------------------------------------------------------------------------------
# 动态定位工程根目录与输入输出路径
# ------------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_loader import load_annex4_dynamic_tariffs
from src.solver_q4 import run_q4_pipeline

RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
FIGURES_DIR = os.path.join(PROJECT_ROOT, "figures")
os.makedirs(FIGURES_DIR, exist_ok=True)
OUTPUT_PATH = os.path.join(FIGURES_DIR, "q4_fig1_dynamic_price_response.png")

# ------------------------------------------------------------------------------
# 1. 全局学术排版与字体配置
# ------------------------------------------------------------------------------
plt.rcParams['font.sans-serif'] = ['SimSun', 'Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['mathtext.fontset'] = 'stix'

plt.rcParams['font.size'] = 10.5
plt.rcParams['axes.titlesize'] = 11.0
plt.rcParams['axes.labelsize'] = 10.5
plt.rcParams['xtick.labelsize'] = 9.0
plt.rcParams['ytick.labelsize'] = 9.0
plt.rcParams['legend.fontsize'] = 8.6
plt.rcParams['figure.titlesize'] = 12.0

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

COLOR_DISCHARGE = "#3B6E8C"    # 储能放电：沉稳灰蓝
COLOR_CHARGE    = "#7FA9C6"    # 储能充电：柔和冷浅青
COLOR_PRICE     = "#B45309"    # 动态电价曲线：低饱和暖赭黄
COLOR_COST_BAR  = "#5A6B7C"    # 全周期总费用柱：中性冷板岩灰
COLOR_EM_BAR    = "#A26053"    # 紧急缺电量柱：低饱和陶土赤红

SIM_START_DAY = 31
REP_DAY_NUMBER = 153
REP_DATE = "2025-07-03"
STEPS_PER_DAY = 144
DELTA_T = 1.0 / 6.0

# ------------------------------------------------------------------------------
# 2. 求解管线执行与代表日数据提取
# ------------------------------------------------------------------------------
print("正在执行问题四求解流水线并提取代表日数据...")
res_q4_2, res_q4_3 = run_q4_pipeline(export=False)
tariffs_dynamic = load_annex4_dynamic_tariffs()

sim_day_idx = REP_DAY_NUMBER - 1
full_year_day_idx = SIM_START_DAY + sim_day_idx
start = sim_day_idx * STEPS_PER_DAY
end = start + STEPS_PER_DAY

p_chg_kwh = np.asarray(res_q4_2["p_chg_kwh"][start:end], dtype=float)
p_dis_kwh = np.asarray(res_q4_2["p_dis_kwh"][start:end], dtype=float)
p_chg_kw = p_chg_kwh / DELTA_T
p_dis_kw = p_dis_kwh / DELTA_T
p_bess_kw = p_dis_kw - p_chg_kw

tariff_day = np.asarray(tariffs_dynamic[full_year_day_idx], dtype=float)
hours = np.arange(STEPS_PER_DAY) / 6.0

peak_step = int(np.argmax(tariff_day))
peak_price = float(tariff_day[peak_step])
peak_hour = hours[peak_step]
peak_h = int(peak_step * 10 // 60)
peak_m = int(peak_step * 10 % 60)

cost_q42 = float(res_q4_2["total_cost"]) / 1e4
cost_q43 = float(res_q4_3["total_cost"]) / 1e4
em_q42 = float(res_q4_2["total_em_kwh"]) / 1e4
em_q43 = float(res_q4_3["total_em_kwh"]) / 1e4

cost_reduction = (cost_q42 - cost_q43) / cost_q42 * 100.0
em_reduction = (em_q42 - em_q43) / em_q42 * 100.0

# ------------------------------------------------------------------------------
# 3. 核心画布绘制与排版
# ------------------------------------------------------------------------------
fig, (ax1, ax2) = plt.subplots(
    1, 2, figsize=(12.0, 4.8), dpi=600,
    gridspec_kw={"width_ratios": [1.45, 1.05], "wspace": 0.38}
)

# (a) 动态电价与储能充放电响应
p_dis_series = np.maximum(0.0, p_bess_kw)
p_chg_series = np.minimum(0.0, p_bess_kw)

ax1.fill_between(hours, 0, p_dis_series, step='post', color=COLOR_DISCHARGE, alpha=0.75,
                 label="储能放电功率 $P_{\\mathrm{dis}}$")
ax1.fill_between(hours, 0, p_chg_series, step='post', color=COLOR_CHARGE, alpha=0.75,
                 label="储能充电功率 $P_{\\mathrm{chg}}$")
ax1.axhline(0, color='#000000', linewidth=0.9, linestyle='-')

ax1.set_xlim(0, 24)
ax1.set_xticks(np.arange(0, 25, 4))
ax1.xaxis.set_major_formatter(FuncFormatter(lambda x, p: f"$\\mathit{{{int(x)}:00}}$"))
ax1.yaxis.set_major_formatter(num_fmt)
ax1.set_xlabel("日内调度时间轴 $t$ / h", fontweight='bold', labelpad=6)
ax1.set_ylabel("储能净功率 / kW", fontweight='bold', labelpad=6)
ax1.set_ylim(-5500, 5800)
ax1.grid(axis="y", linestyle=":", alpha=0.45)

# 第二纵轴：动态电价曲线
ax1_price = ax1.twinx()
ax1_price.step(hours, tariff_day, where='post', color=COLOR_PRICE, linewidth=1.8,
               label="动态实时电价 $c(t)$", zorder=5)
ax1_price.scatter(peak_hour, peak_price, s=36, color=COLOR_PRICE, edgecolors='#000000', lw=0.8, zorder=6)
ax1_price.yaxis.set_major_formatter(num_fmt)
ax1_price.set_ylabel("实时电价 / (元 / kWh)", fontweight='bold', labelpad=6, color=COLOR_PRICE)
ax1_price.set_ylim(0.25, 2.35)

ax1_price.annotate(
    f"尖峰极值: $\\mathit{{{peak_price:.4f}}}$ 元\n$\\mathit{{{peak_h:02d}:{peak_m:02d}}}$",
    xy=(peak_hour, peak_price),
    xytext=(peak_hour - 5.2, peak_price + 0.12),
    arrowprops=dict(arrowstyle="->", color=COLOR_PRICE, linewidth=1.0, shrinkB=4),
    fontsize=8.5,
    ha="center",
    va="bottom",
    color=COLOR_PRICE,
    fontweight='bold'
)

h1, l1 = ax1.get_legend_handles_labels()
h2, l2 = ax1_price.get_legend_handles_labels()
ax1.legend(h1 + h2, l1 + l2, loc="upper left", frameon=False, fontsize=8.4)
ax1.set_title(f"(a) 动态电价与储能削峰填谷响应（{REP_DATE}）", loc="left", fontweight='bold', pad=10)

# (b) 动态电价下两种调度策略比较
x = np.array([0, 1])
w = 0.26

bars_cost = ax2.bar(
    x - w/2.0, [cost_q42, cost_q43],
    width=w, color=COLOR_COST_BAR, edgecolor='#000000', lw=1.0,
    label="全周期总费用 (左轴)"
)
ax2.set_xticks(x)
ax2.set_xticklabels(["Q4-2\n两阶段鲁棒策略", "Q4-3\n滚动预测策略"], fontweight='bold', fontsize=9.2)
ax2.set_ylabel("全周期总购电费用 / 万元", fontweight='bold', labelpad=6, color=COLOR_COST_BAR)

ax2.set_ylim(1450, 1750)
ax2.yaxis.set_major_formatter(num_fmt)
ax2.grid(axis="y", linestyle=":", alpha=0.45)

for bar, val in zip(bars_cost, [cost_q42, cost_q43]):
    ax2.text(
        bar.get_x() + bar.get_width()/2.0, val + 6,
        f"$\\mathit{{{val:.2f}}}$",
        ha="center", va="bottom", fontsize=8.8, fontweight="bold", color=COLOR_COST_BAR
    )

ax2_em = ax2.twinx()
bars_em = ax2_em.bar(
    x + w/2.0, [em_q42, em_q43],
    width=w, color=COLOR_EM_BAR, edgecolor='#000000', lw=1.0,
    label="紧急购电量 (右轴)"
)
ax2_em.set_ylabel("紧急购电量 / 万kWh", fontweight='bold', labelpad=6, color=COLOR_EM_BAR)
ax2_em.set_ylim(0, 16.5)
ax2_em.yaxis.set_major_formatter(num_fmt)

for bar, val in zip(bars_em, [em_q42, em_q43]):
    ax2_em.text(
        bar.get_x() + bar.get_width()/2.0, val + 0.35,
        f"$\\mathit{{{val:.2f}}}$",
        ha="center", va="bottom", fontsize=8.8, fontweight="bold", color=COLOR_EM_BAR
    )

hb1, lb1 = ax2.get_legend_handles_labels()
hb2, lb2 = ax2_em.get_legend_handles_labels()
ax2.legend(hb1 + hb2, lb1 + lb2, loc="upper right", frameon=False, fontsize=8.4)

summary_tag = (
    f"总成本降幅: $\\mathit{{{cost_reduction:.2f}\\%}}$\n"
    f"缺电量压降: $\\mathit{{{em_reduction:.2f}\\%}}$"
)
ax2.text(
    0.50, 13.0, summary_tag,
    ha="center", va="center", fontsize=8.5, fontweight="bold", color="#166534",
    bbox=dict(boxstyle='round,pad=0.35', facecolor='#F0FDF4', edgecolor='#166534', lw=0.8)
)
ax2.set_title("(b) 动态电价下两类调度策略经济性比较", loc="left", fontweight='bold', pad=10)

# ------------------------------------------------------------------------------
# 4. 全局标题与导出
# ------------------------------------------------------------------------------
fig.suptitle(
    "问题四动态电价下储能微网响应与调度策略经济性比较",
    fontsize=11.8, fontweight="bold", y=0.98
)

fig.subplots_adjust(top=0.88, bottom=0.13, left=0.08, right=0.92, wspace=0.35)
plt.savefig(OUTPUT_PATH, dpi=600)
plt.close()
print(f"[通过 PASS] 问题四 图 1 已成功生成: {OUTPUT_PATH}")