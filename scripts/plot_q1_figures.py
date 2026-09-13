#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
全国大学生数学建模竞赛 (CUMCM) 论文核心学术级配图脚本 (问题 1)
输出图表: figures/ (q1_fig1, q1_fig2, q1_fig3，印刷级 600 DPI 分辨率)
标准规范: GB 3100~3102-1993 量和单位规范、宋体+Times New Roman混排、五号/小五号字梯度
================================================================================
"""

import os
import sys
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

DEFAULT_DATA1_PATH = os.path.join(RESULTS_DIR, "result1.xlsx")
DEFAULT_FIG1_PATH = os.path.join(FIGURES_DIR, "q1_fig1_diurnal_grid_procurement.png")
DEFAULT_FIG2_PATH = os.path.join(FIGURES_DIR, "q1_fig2_bess_energy_balance.png")
DEFAULT_FIG3_PATH = os.path.join(FIGURES_DIR, "q1_fig3_polar_cumulative_spectrum.png")

# ------------------------------------------------------------------------------
# 1. 国赛标准排版与字号层级全局预设
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
plt.rcParams['legend.fontsize'] = 9.0
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
plt.rcParams['xtick.major.width'] = 1.1
plt.rcParams['ytick.major.width'] = 1.1

def italic_formatter(val, pos):
    if abs(val - int(val)) < 1e-5:
        return f"$\\mathit{{{int(val)}}}$"
    return f"$\\mathit{{{val:.1f}}}$"

num_fmt = FuncFormatter(italic_formatter)

# 低饱和度学术配色体系
COLOR_GRID = "#2F4F4F"        # 计划购电：板岩冷灰绿
COLOR_CHG = "#326273"         # 储能充电：低饱和深青蓝
COLOR_DIS = "#B5533C"         # 储能放电：赤陶红
COLOR_SOC = "#4A7C59"         # 储能状态：鼠尾草绿
COLOR_ZERO = "#ECF1F4"        # 自主零购电区间：极淡蓝灰填充
COLOR_ACCENT = "#C87D28"      # 峰值标注：暗金/赭黄

grid_purchase_kwh = np.array([
    1406.6411, 1406.3299, 1407.3839, 1409.0740, 1409.8046, 576.6400,
    577.8597,  577.9939,  911.1614,  580.4154,  582.5140,  583.0740,
    584.2049,  585.4398,  586.1447,  586.3208,  586.4253,  586.8496,
    587.8210,  589.5476,  590.8135,  590.2131,  591.0663,  593.3678,
    593.6597,  592.7864,  593.3379,  596.6758,  597.7802,  595.1625,
    590.6065,  589.4852,  578.4554,  1383.6598, 591.1402,  0.0000,
    0.0000,    0.0000,    0.0000,    0.0000,    0.0000,    0.0000,
    0.0000,    0.0000,    0.0000,    0.0000,    0.0000,    0.0000,
    0.0000,    0.0000,    0.0000,    0.0000,    0.0000,    0.0000,
    0.0000,    0.0000,    0.0000,    0.0000,    0.0000,    0.0000,
    0.0000,    0.0000,    0.0000,    0.0000,    0.0000,    0.0000,
    0.0000,    575.1709,  0.0000,    0.0000,    179.2772,  520.1245,
    486.4029,  480.4124,  485.3000,  488.6070,  498.2707,  0.0000,
    0.0000,    0.0000,    0.0000,    0.0000,    0.0000,    0.0000,
    0.0000,    0.0000,    0.0000,    0.0000,    0.0000,    0.0000,
    112.0899,  266.7327,  197.5235,  244.8140,  295.5346,  345.7775,
    394.9315,  445.4317,  495.6966,  547.1190,  599.9854,  635.4297,
    660.8307,  702.0369,  738.0658,  775.9447,  826.0832,  762.4228,
    636.9826,  531.8940,  678.8305,  686.2685,  696.5044,  0.0000,
    0.0000,    0.0000,    0.0000,    0.0000,    0.0000,    0.0000,
    0.0000,    0.0000,    0.0000,    0.0000,    0.0000,    715.8689,
    717.0051,  720.1603,  717.0549,  720.4460,  738.1347,  671.6936,
    1393.7903, 1384.8989, 568.8260,  1396.9886, 1397.7599, 566.7474,
    1399.8738, 567.8302,  569.3586,  1403.6635, 904.9487,  573.1768
])

bess_periods = [
    "0:00–4:00", "4:00–8:00", "8:00–12:00",
    "12:00–16:00", "16:00–20:00", "20:00–24:00"
]
charge_kwh = np.array([4500.0, 833.3333, 4787.9643, 5286.0352, 0.0, 5333.3333])
discharge_kwh = np.array([0.0, 6365.8412, 1702.9970, 91.1014, 5780.1319, 2859.8681])
soc_initial_kwh = 6000.0
soc_terminal_kwh = 6000.0


# ------------------------------------------------------------------------------
# 图 1：日前计划购电时序阶梯曲线与消纳区间图
# ------------------------------------------------------------------------------
def plot_figure_1(save_path=DEFAULT_FIG1_PATH, data_path=DEFAULT_DATA1_PATH):
    if os.path.exists(data_path):
        df_grid = pd.read_excel(data_path, sheet_name="计划购电量")
        purchase_data = df_grid.iloc[:, 1].dropna().values.astype(float)
    else:
        purchase_data = grid_purchase_kwh.copy()
        
    n_steps = len(purchase_data)
    t_hours = np.linspace(0, 24, n_steps, endpoint=False)
    
    fig, ax = plt.subplots(figsize=(8.2, 4.2), dpi=600)
    
    zero_mask = (purchase_data == 0.0)
    in_zero = False
    start_t = 0.0
    for idx, is_z in enumerate(zero_mask):
        if is_z and not in_zero:
            in_zero = True
            start_t = t_hours[idx]
        elif not is_z and in_zero:
            in_zero = False
            ax.axvspan(start_t, t_hours[idx], color=COLOR_ZERO, alpha=0.8, lw=0,
                      label="微网自主消纳运行区间" if start_t < 6.5 else "")
    if in_zero:
        ax.axvspan(start_t, 24.0, color=COLOR_ZERO, alpha=0.8, lw=0)

    time_steps = np.append(t_hours, 24.0)
    proc_steps = np.append(purchase_data, purchase_data[-1])
    
    ax.step(time_steps, proc_steps, where='post', color=COLOR_GRID, lw=1.6,
            label="计划购电量 $Q_{\\mathrm{grid}}(t)$")
    ax.fill_between(time_steps, 0, proc_steps, step='post', color=COLOR_GRID, alpha=0.18, lw=0)

    max_val = np.max(purchase_data)
    max_idx = np.argmax(purchase_data)
    max_t = t_hours[max_idx]
    
    ax.scatter([max_t], [max_val], color=COLOR_ACCENT, s=36, zorder=5, edgecolors='black', lw=0.9)
    ax.annotate(f"购电峰值: $\\mathit{{{max_val:.2f}}}$ kWh\n(时段 00:40–00:50)",
                xy=(max_t, max_val), xytext=(max_t + 0.8, 1475),
                arrowprops=dict(arrowstyle="->", color="black", lw=0.9,
                                connectionstyle="arc3,rad=-0.1"),
                fontsize=9.0, va='bottom')

    ax.set_xlim(-0.1, 24.1)
    ax.set_ylim(0, 1680)
    ax.set_xticks(np.arange(0, 25, 2))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, p: f"$\\mathit{{{int(x)}:00}}$"))
    ax.yaxis.set_major_formatter(num_fmt)
    
    ax.set_xlabel("调度时间 $t$ / h", fontweight='bold', labelpad=6)
    ax.set_ylabel("计划购电量 $Q_{\\mathrm{grid}}$ / (kWh / 10 min)", fontweight='bold', labelpad=6)
    ax.set_title("(a) 典型日全时域计划购电阶梯时序曲线 (144个时步)",
                 loc='left', fontweight='bold', pad=8)
    
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend(loc="upper right", frameon=True, edgecolor='#000000', framealpha=1.0, facecolor='#FFFFFF')
    
    total_kwh = np.sum(purchase_data)
    zero_count = int(np.sum(zero_mask))
    zero_ratio = (zero_count / float(n_steps)) * 100.0
    text_summary = (
        f"全天累计购电量: $\\mathit{{{total_kwh:.2f}}}$ kWh\n"
        f"单步最大购电量: $\\mathit{{{max_val:.2f}}}$ kWh\n"
        f"零购电运行步数: $\\mathit{{{zero_count}}}$ / $\\mathit{{{n_steps}}}$ ($\\mathit{{{zero_ratio:.1f}\\%}}$)"
    )
    ax.text(0.28, 0.56, text_summary, transform=ax.transAxes,
            bbox=dict(boxstyle='square,pad=0.5', facecolor='#FFFFFF', edgecolor='#000000', lw=0.9),
            fontsize=9.0)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=600)
    plt.close()
    print(f"[通过 PASS] 问题一 图 1 已成功生成: {save_path}")


# ------------------------------------------------------------------------------
# 图 2：储能系统分时段双向吞吐与首末闭环柱状图
# ------------------------------------------------------------------------------
def plot_figure_2(save_path=DEFAULT_FIG2_PATH):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.5, 4.0), dpi=600,
                                   gridspec_kw={'width_ratios': [3.5, 1.2]})
    
    x = np.arange(len(bess_periods))
    bar_width = 0.52
    
    bars_chg = ax1.bar(x, charge_kwh, width=bar_width, color=COLOR_CHG, edgecolor='#000000',
                       lw=1.0, label="充电量 $E_{\\mathrm{ch}}$ (+)")
    bars_dis = ax1.bar(x, -discharge_kwh, width=bar_width, color=COLOR_DIS, edgecolor='#000000',
                       lw=1.0, label="放电量 $E_{\\mathrm{dis}}$ ($-$)")
    
    ax1.axhline(0, color='#000000', lw=1.2)
    
    for bar in bars_chg:
        height = bar.get_height()
        if height > 400:
            ax1.text(bar.get_x() + bar.get_width()/2.0, height + 180,
                     f"$\\mathit{{{height:.1f}}}$", ha='center', va='bottom',
                     fontsize=8.5)
    for bar in bars_dis:
        height = bar.get_height()
        if abs(height) > 400:
            ax1.text(bar.get_x() + bar.get_width()/2.0, height - 250,
                     f"$\\mathit{{{abs(height):.1f}}}$", ha='center', va='top',
                     fontsize=8.5)
            
    ax1.set_xticks(x)
    ax1.set_xticklabels(bess_periods, rotation=18, ha='right')
    ax1.set_ylim(-7500, 8000)
    ax1.yaxis.set_major_formatter(num_fmt)
    ax1.set_ylabel("聚合电量 / (kWh / 4 h)", fontweight='bold', labelpad=6)
    ax1.set_title("(a) 储能系统分时段双向充放电调度动态", loc='left', fontweight='bold', pad=8)
    ax1.grid(True, linestyle=":", axis='y', alpha=0.5)
    ax1.legend(loc="upper left", frameon=True, edgecolor='#000000', framealpha=1.0)
    
    soc_points = [soc_initial_kwh, soc_terminal_kwh]
    soc_labels = ["0:00 初始", "24:00 终止"]
    x_soc = np.arange(2)
    
    bars_soc = ax2.bar(x_soc, soc_points, width=0.45, color=COLOR_SOC,
                       edgecolor='#000000', lw=1.0)
    ax2.axhline(6000.0, color='#000000', linestyle='--', lw=1.0)
    for bar in bars_soc:
        h = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2.0, h + 150,
                 f"$\\mathit{{{h:.1f}}}$", ha='center', va='bottom',
                 fontsize=8.5)
                 
    ax2.set_xticks(x_soc)
    ax2.set_xticklabels(soc_labels, rotation=18, ha='right')
    ax2.set_ylim(0, 8000)
    ax2.yaxis.set_major_formatter(num_fmt)
    ax2.set_ylabel("电池储电量 / kWh", fontweight='bold', labelpad=4)
    ax2.set_title("(b) 首末状态闭环", loc='left', fontweight='bold', pad=8)
    ax2.grid(True, linestyle=":", axis='y', alpha=0.5)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=600)
    plt.close()
    print(f"[通过 PASS] 问题一 图 2 已成功生成: {save_path}")


# ------------------------------------------------------------------------------
# 图 3：24小时极坐标昼夜相图与经验分布谱
# ------------------------------------------------------------------------------
def plot_figure_3(save_path=DEFAULT_FIG3_PATH, data_path=DEFAULT_DATA1_PATH):
    if os.path.exists(data_path):
        df_grid = pd.read_excel(data_path, sheet_name="计划购电量")
        purchase_data = df_grid.iloc[:, 1].dropna().values.astype(float)
    else:
        purchase_data = grid_purchase_kwh.copy()

    n_steps = len(purchase_data)
    fig = plt.figure(figsize=(9.0, 4.2), dpi=600)
    
    # 子图 (a)：极坐标时钟相位图
    ax_polar = fig.add_subplot(1, 2, 1, projection='polar')
    theta = np.linspace(0, 2 * np.pi, n_steps, endpoint=False)
    ax_polar.set_theta_direction(-1)
    ax_polar.set_theta_offset(np.pi / 2.0)
    
    width = (2 * np.pi) / float(n_steps)
    norm = mpl.colors.Normalize(vmin=0, vmax=np.max(purchase_data))
    cmap = mpl.cm.cividis
    colors = cmap(norm(purchase_data))
    
    ax_polar.bar(theta, purchase_data, width=width, bottom=150.0,
                 color=colors, edgecolor='none', alpha=0.92)
    
    clock_ticks = np.linspace(0, 2 * np.pi, 8, endpoint=False)
    clock_labels = [f"$\\mathit{{{h}:00}}$" for h in [0, 3, 6, 9, 12, 15, 18, 21]]
    ax_polar.set_xticks(clock_ticks)
    ax_polar.set_xticklabels(clock_labels, fontsize=9.0)
    
    ax_polar.set_yticks([500, 1000, 1500])
    ax_polar.yaxis.set_major_formatter(num_fmt)
    ax_polar.set_rlabel_position(105)
    for label in ax_polar.get_yticklabels():
        label.set_bbox(dict(facecolor='white', edgecolor='none', alpha=0.85, pad=0.6))
        
    ax_polar.set_title("(a) 24小时极坐标购电昼夜节律相图", loc='left', fontweight='bold', pad=14)
    
    # 子图 (b)：ECDF 累积概率分布曲线
    ax_ecdf = fig.add_subplot(1, 2, 2)
    sorted_purchase = np.sort(purchase_data)
    ecdf = np.arange(1, n_steps + 1) / float(n_steps)
    
    ax_ecdf.step(sorted_purchase, ecdf, where='post', color=COLOR_GRID, lw=1.8,
                 label="经验累积概率分布 (ECDF)")
    
    zero_mask = (sorted_purchase <= 1e-4)
    zero_count = int(np.sum(zero_mask))
    zero_pct = zero_count / float(n_steps)
    
    ax_ecdf.scatter([0.0], [zero_pct], color=COLOR_ACCENT, s=40, zorder=5, edgecolors='black', lw=0.8)
    ax_ecdf.annotate(f"零购电时步占比:\n$\\mathit{{{zero_pct*100:.1f}\\%}}$ (共 $\\mathit{{{zero_count}}}$ 个时步)",
                     xy=(0.0, zero_pct), xytext=(180, 0.25),
                     arrowprops=dict(arrowstyle="->", color="black", lw=0.9),
                     fontsize=9.0)
                     
    ax_ecdf.set_xlim(-20, 1550)
    ax_ecdf.set_ylim(0, 1.05)
    ax_ecdf.xaxis.set_major_formatter(num_fmt)
    ax_ecdf.yaxis.set_major_formatter(num_fmt)
    ax_ecdf.set_xlabel("单步计划购电量 $Q_{\\mathrm{grid}}$ / kWh", fontweight='bold', labelpad=6)
    ax_ecdf.set_ylabel("经验累积概率 $F(x)$", fontweight='bold', labelpad=6)
    ax_ecdf.set_title("(b) 购电强度累积概率分布", loc='left', fontweight='bold', pad=8)
    ax_ecdf.grid(True, linestyle=":", alpha=0.5)
    ax_ecdf.legend(loc="lower right", frameon=True, edgecolor='#000000', framealpha=1.0)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=600)
    plt.close()
    print(f"[通过 PASS] 问题一 图 3 已成功生成: {save_path}")


if __name__ == "__main__":
    print("==================================================================")
    print("正在生成问题一论文核心学术图表...")
    print("==================================================================")
    plot_figure_1(DEFAULT_FIG1_PATH, DEFAULT_DATA1_PATH)
    plot_figure_2(DEFAULT_FIG2_PATH)
    plot_figure_3(DEFAULT_FIG3_PATH, DEFAULT_DATA1_PATH)
    print("==================================================================")
    print(f"问题一全套图表已成功归档至: {FIGURES_DIR}")
    print("==================================================================")