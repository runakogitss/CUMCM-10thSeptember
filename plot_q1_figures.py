#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
全国大学生数学建模竞赛 (CUMCM) 论文核心学术级高清配图脚本 (问题 1)
标准规范: 国赛最高评阅标准 (GB标准量与单位、宋体+Times New Roman混排、五号/小五号字阶梯)
输出目录: figures/ (Figure1, Figure2, Figure3，默认 600 DPI 印刷级分辨率)
================================================================================
"""

import os
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

# ==============================================================================
# 1. 国赛标准排版与字号层级全局预设 (CUMCM Formatting Preset)
# ==============================================================================
# 字体族：优先匹配 Windows 系统自带宋体 (SimSun) 与 Times New Roman
plt.rcParams['font.sans-serif'] = ['SimSun', 'Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.unicode_minus'] = False  # 杜绝负号显示为乱码方块

# 数学公式字体：STIX 系列，完美对接 Times New Roman 斜体
plt.rcParams['mathtext.fontset'] = 'stix'

# 严格对照国赛排版标准的字号体系 (五号 10.5 pt，小五号 9.0 pt)
plt.rcParams['font.size'] = 10.5          # 基准五号字
plt.rcParams['axes.titlesize'] = 10.5     # 子图标题：五号加粗
plt.rcParams['axes.labelsize'] = 10.5     # 坐标轴名称：五号
plt.rcParams['xtick.labelsize'] = 9.0     # 刻度数字：小五号
plt.rcParams['ytick.labelsize'] = 9.0     # 刻度数字：小五号
plt.rcParams['legend.fontsize'] = 9.0     # 图例文字：小五号
plt.rcParams['figure.titlesize'] = 12.0   # 总图标题：小四号

# 坐标轴边框加固与刻度朝向 (符合科技期刊印刷规范)
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

# 数值斜体格式化 (国赛标准：数学符号与斜体数值统一)
def italic_formatter(val, pos):
    if abs(val - int(val)) < 1e-5:
        return f"$\\mathit{{{int(val)}}}$"
    else:
        return f"$\\mathit{{{val:.1f}}}$"

num_fmt = FuncFormatter(italic_formatter)

# 国赛专著级沉稳低饱和度配色方案
COLOR_GRID = "#2F4F4F"        # 计划购电：板岩冷灰绿
COLOR_CHG = "#326273"         # 储能充电：低饱和深青蓝
COLOR_DIS = "#B5533C"         # 储能放电：赤陶红（印刷高反差）
COLOR_SOC = "#4A7C59"         # 储能状态：鼠尾草绿
COLOR_ZERO = "#ECF1F4"        # 自主零购电区间：极淡蓝灰填充
COLOR_ACCENT = "#C87D28"      # 峰值标注：暗金/赭黄

# ==============================================================================
# 2. 定量数据输入 (源自 Q1 标准规划求解输出 result1)
# ==============================================================================
# 144 步购电量 (kWh / 10-min)
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

time_hours = np.linspace(0, 24, 144, endpoint=False)

# 储能 6 个 4 小时间隔及首末状态
bess_periods = [
    "0:00–4:00", "4:00–8:00", "8:00–12:00",
    "12:00–16:00", "16:00–20:00", "20:00–24:00"
]
charge_kwh = np.array([4500.0, 833.3333, 4787.9643, 5286.0352, 0.0, 5333.3333])
discharge_kwh = np.array([0.0, 6365.8412, 1702.9970, 91.1014, 5780.1319, 2859.8681])
soc_initial_kwh = 6000.0
soc_terminal_kwh = 6000.0


# ==============================================================================
# 图 1：日前计划购电时序阶梯曲线与消纳区间图 (国赛中文规范)
# ==============================================================================
def plot_figure_1(save_path="figures/Figure1_Diurnal_Grid_Procurement_Profile.png", data_path="results/result1.xlsx"):
    import os
    import pandas as pd
    
    # 1. 动态加载求解输出文件，彻底消除硬编码与终端数据不一致的缺陷
    if os.path.exists(data_path):
        df_grid = pd.read_excel(data_path, sheet_name="计划购电量")
        purchase_data = df_grid.iloc[:, 1].dropna().values.astype(float)
    else:
        purchase_data = grid_purchase_kwh.copy()
        
    n_steps = len(purchase_data)
    t_hours = np.linspace(0, 24, n_steps, endpoint=False)
    
    fig, ax = plt.subplots(figsize=(8.2, 4.2), dpi=600)
    
    # 2. 微网自主消纳背景填充
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

    # 3. 阶梯购电曲线
    time_steps = np.append(t_hours, 24.0)
    proc_steps = np.append(purchase_data, purchase_data[-1])
    
    ax.step(time_steps, proc_steps, where='post', color=COLOR_GRID, lw=1.6,
            label="计划购电量 $Q_{\\mathrm{grid}}(t)$")
    ax.fill_between(time_steps, 0, proc_steps, step='post', color=COLOR_GRID, alpha=0.18, lw=0)

    # 4. 峰值标注（抬升至 y=1475 空白层，避让右侧阶梯波形）
    max_val = np.max(purchase_data)
    max_idx = np.argmax(purchase_data)
    max_t = t_hours[max_idx]
    
    ax.scatter([max_t], [max_val], color=COLOR_ACCENT, s=36, zorder=5, edgecolors='black', lw=0.9)
    ax.annotate(f"购电峰值: $\\mathit{{{max_val:.2f}}}$ kWh\n(时段 00:40–00:50)",
                xy=(max_t, max_val), xytext=(max_t + 0.8, 1475),
                arrowprops=dict(arrowstyle="->", color="black", lw=0.9,
                                connectionstyle="arc3,rad=-0.1"),
                fontsize=9.0, va='bottom')

    # 5. 坐标轴格式化
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
    
    # 6. 统计框动态取值（精准绑定 59482.70 kWh）
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
    print(f"[SUCCESS] 图 1 动态更新完成: {save_path} (累计购电量: {total_kwh:.2f} kWh)")


def plot_figure_2(save_path="figures/Figure2_BESS_Energy_Balance_Diverging.png"):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.5, 4.0), dpi=600,
                                   gridspec_kw={'width_ratios': [3.5, 1.2]})
    
    x = np.arange(len(bess_periods))
    bar_width = 0.52
    
    bars_chg = ax1.bar(x, charge_kwh, width=bar_width, color=COLOR_CHG, edgecolor='#000000',
                       lw=1.0, label="充电量 $E_{\\mathrm{ch}}$ (+)")
    # 修复字符集方块乱码：使用 LaTeX 形式的 ($-$)
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
    print(f"[SUCCESS] 图 2 格式微调完成: {save_path}")


# ==============================================================================
# 图 3：24小时极坐标昼夜相图与经验分布谱 (国赛中文规范)
# ==============================================================================
def plot_figure_3(save_path="figures/Figure3_Polar_Phase_and_Cumulative_Spectrum.png"):
    fig = plt.figure(figsize=(9.0, 4.2), dpi=600)
    
    # 子图 (a)：极坐标时钟相位图 (顺时针 0:00 在顶部)
    ax_polar = fig.add_subplot(1, 2, 1, projection='polar')
    theta = np.linspace(0, 2 * np.pi, 144, endpoint=False)
    ax_polar.set_theta_direction(-1)
    ax_polar.set_theta_offset(np.pi / 2.0)
    
    width = (2 * np.pi) / 144.0
    norm = mpl.colors.Normalize(vmin=0, vmax=np.max(grid_purchase_kwh))
    cmap = mpl.cm.cividis
    colors = cmap(norm(grid_purchase_kwh))
    
    ax_polar.bar(theta, grid_purchase_kwh, width=width, bottom=150.0,
                 color=colors, edgecolor='none', alpha=0.92)
    
    clock_ticks = np.linspace(0, 2 * np.pi, 8, endpoint=False)
    clock_labels = [f"$\\mathit{{{h}:00}}$" for h in [0, 3, 6, 9, 12, 15, 18, 21]]
    ax_polar.set_xticks(clock_ticks)
    ax_polar.set_xticklabels(clock_labels, fontsize=9.0)
    
    ax_polar.set_yticks([500, 1000, 1500])
    ax_polar.yaxis.set_major_formatter(num_fmt)
    ax_polar.set_rlabel_position(115)
    ax_polar.set_title("(a) 24小时极坐标购电昼夜节律相图", loc='left', fontweight='bold', pad=14)
    
    # 子图 (b)：ECDF 累积概率分布曲线
    ax_ecdf = fig.add_subplot(1, 2, 2)
    sorted_purchase = np.sort(grid_purchase_kwh)
    ecdf = np.arange(1, len(sorted_purchase) + 1) / float(len(sorted_purchase))
    
    ax_ecdf.step(sorted_purchase, ecdf, where='post', color=COLOR_GRID, lw=1.8,
                 label="经验累积概率分布 (ECDF)")
    
    zero_count = int(np.sum(sorted_purchase == 0.0))
    zero_pct = zero_count / 144.0
    
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
    print(f"[SUCCESS] 国赛标准图 3 已生成: {save_path}")


# ==============================================================================
# 4. 执行入口
# ==============================================================================
if __name__ == "__main__":
    os.makedirs("figures", exist_ok=True)
    print("==================================================================")
    print("正在按 CUMCM 全国一等奖标准生成高清论文核心图表...")
    print("==================================================================")
    plot_figure_1("figures/Figure1_Diurnal_Grid_Procurement_Profile.png")
    plot_figure_2("figures/Figure2_BESS_Energy_Balance_Diverging.png")
    plot_figure_3("figures/Figure3_Polar_Phase_and_Cumulative_Spectrum.png")
    print("==================================================================")
    print("全套配图已成功导出至 figures/ 目录 (600 DPI, 符合国赛格式规范)")
    print("==================================================================")