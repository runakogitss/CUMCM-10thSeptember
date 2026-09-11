#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
Publication-Grade Scientific Data Visualization Suite for CUMCM 2026 Problem C (Q1)
Dataset Source: result1 (144-step Grid Purchase, 6-period BESS Charge/Discharge, SoC Loop)
Styling Standard: Nature / Science Guidelines (White background, Times New Roman 11pt,
                  Italic Numerics, Heavy Axis Weight, Low-Saturation Scientific Colormaps)
================================================================================
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.ticker import FuncFormatter

# ==============================================================================
# 1. GLOBAL SCIENTIFIC FORMATTING & JOURNAL-GRADE PRESETS
# ==============================================================================
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif']
plt.rcParams['font.size'] = 11.0
plt.rcParams['axes.titlesize'] = 11.0
plt.rcParams['axes.labelsize'] = 11.0
plt.rcParams['xtick.labelsize'] = 11.0
plt.rcParams['ytick.labelsize'] = 11.0
plt.rcParams['legend.fontsize'] = 9.5
plt.rcParams['figure.titlesize'] = 12.0

# Scientific Canvas & Spines
plt.rcParams['figure.facecolor'] = '#FFFFFF'
plt.rcParams['axes.facecolor'] = '#FFFFFF'
plt.rcParams['axes.edgecolor'] = '#000000'
plt.rcParams['axes.linewidth'] = 1.3
plt.rcParams['grid.linewidth'] = 0.5
plt.rcParams['grid.alpha'] = 0.35
plt.rcParams['grid.color'] = '#7F7F7F'

# Ticks configuration (Nature standard: ticks pointing inside)
plt.rcParams['xtick.direction'] = 'in'
plt.rcParams['ytick.direction'] = 'in'
plt.rcParams['xtick.major.size'] = 5.0
plt.rcParams['ytick.major.size'] = 5.0
plt.rcParams['xtick.major.width'] = 1.2
plt.rcParams['ytick.major.width'] = 1.2
plt.rcParams['mathtext.fontset'] = 'stix'

# Number Italicization Formatter (Strict requirement: all numeric values italic)
def italic_formatter(val, pos):
    if abs(val - int(val)) < 1e-5:
        return f"$\\mathit{{{int(val)}}}$"
    else:
        return f"$\\mathit{{{val:.1f}}}$"

num_fmt = FuncFormatter(italic_formatter)

# Low-saturation scientific color palette (Muted Cividis / Batlow inspired)
COLOR_GRID = "#2F4F4F"        # Muted Slate Dark
COLOR_CHG = "#3B6E8C"         # Softened Deep Teal
COLOR_DIS = "#B05C42"         # Low-saturation Terracotta
COLOR_SOC = "#4A7C59"         # Muted Sage Forest
COLOR_ZERO = "#E6ECEF"        # Very light neutral grey-blue for zero-purchase zones
COLOR_ACCENT = "#D48B38"      # Warm Ochre highlight

# ==============================================================================
# 2. EXACT QUANTITATIVE DATASET EXTRACTION (Strictly from uploaded result1)
# ==============================================================================
# 144 steps (10-minute resolution, total 24 hours, unit: kWh)
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

# Time axes (144 bins = 24 hours, step = 1/6 h = 10 min)
time_hours = np.linspace(0, 24, 144, endpoint=False)

# Aggregated 4-hour BESS intervals
bess_periods = [
    "0:00–4:00", "4:00–8:00", "8:00–12:00",
    "12:00–16:00", "16:00–20:00", "20:00–24:00"
]
charge_kwh = np.array([4500.0, 833.3333, 4787.9643, 5286.0352, 0.0, 5333.3333])
discharge_kwh = np.array([0.0, 6365.8412, 1702.9970, 91.1014, 5780.1319, 2859.8681])
soc_initial_kwh = 6000.0
soc_terminal_kwh = 6000.0

# ==============================================================================
# FIGURE 1: HIGH-TEMPORAL-RESOLUTION CHRONOLOGICAL STEP & REGIME PROFILE
# ==============================================================================
def plot_figure_1(save_path="Figure1_Diurnal_Grid_Procurement_Profile.png"):
    fig, ax = plt.subplots(figsize=(8.2, 4.2), dpi=600)
    
    # 1. Shading for Autonomous Zero-Purchase Regimes (Clean Energy/Storage Autarky)
    zero_mask = (grid_purchase_kwh == 0.0)
    in_zero = False
    start_t = 0
    for idx, is_z in enumerate(zero_mask):
        if is_z and not in_zero:
            in_zero = True
            start_t = time_hours[idx]
        elif not is_z and in_zero:
            in_zero = False
            ax.axvspan(start_t, time_hours[idx], color=COLOR_ZERO, alpha=0.7, lw=0,
                      label="Autonomous Zero-Purchase Window" if start_t < 6.5 else "")
    if in_zero:
        ax.axvspan(start_t, 24.0, color=COLOR_ZERO, alpha=0.7, lw=0)

    # 2. Plot Step Function of Discrete 10-Minute Energy Procurement
    time_steps = np.append(time_hours, 24.0)
    proc_steps = np.append(grid_purchase_kwh, grid_purchase_kwh[-1])
    
    ax.step(time_steps, proc_steps, where='post', color=COLOR_GRID, lw=1.6,
            label="Planned Grid Purchase $Q_{\\mathrm{grid}}(t)$")
    ax.fill_between(time_steps, 0, proc_steps, step='post', color=COLOR_GRID, alpha=0.18, lw=0)

    # 3. Peak & Baseline Benchmarks
    max_val = np.max(grid_purchase_kwh)
    max_idx = np.argmax(grid_purchase_kwh)
    max_t = time_hours[max_idx]
    
    ax.scatter([max_t], [max_val], color=COLOR_ACCENT, s=32, zorder=5, edgecolors='black', lw=0.8)
    ax.annotate(f"Peak: $\\mathit{{{max_val:.2f}}}$ kWh\n(t = 00:40–00:50)",
                xy=(max_t, max_val), xytext=(max_t + 1.2, max_val - 120),
                arrowprops=dict(arrowstyle="->", color="black", lw=0.9),
                fontsize=9.5, family='Times New Roman')

    # 4. Axes & Labels Styling
    ax.set_xlim(0, 24)
    ax.set_ylim(0, 1650)
    ax.set_xticks(np.arange(0, 25, 2))
    ax.set_xticklabels([f"$\\mathit{{{h}:00}}$" if h%4==0 else "" for h in range(0, 25, 2)])
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, p: f"$\\mathit{{{int(x)}:00}}$"))
    ax.yaxis.set_major_formatter(num_fmt)
    
    ax.set_xlabel("Diurnal Time Horizon $t$ (Hours)", fontweight='bold', labelpad=6)
    ax.set_ylabel("Planned Energy Purchase $Q_{\\mathrm{grid}}$ (kWh / 10-min)", fontweight='bold', labelpad=6)
    ax.set_title("(a) Diurnal Chronological Grid Purchase Schedule (144 Intervals)",
                 loc='left', fontweight='bold', pad=8)
    
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend(loc="upper right", frameon=True, edgecolor='#000000', framealpha=1.0, facecolor='#FFFFFF')
    
    # Quantitative Summary Inset Text Box
    total_kwh = np.sum(grid_purchase_kwh)
    zero_ratio = (np.sum(zero_mask) / 144.0) * 100.0
    text_summary = (
        f"Daily Aggregate: $\\mathit{{{total_kwh:.2f}}}$ kWh\n"
        f"Peak 10-min: $\\mathit{{{max_val:.2f}}}$ kWh\n"
        f"Zero-Grid Steps: $\\mathit{{{np.sum(zero_mask)}}}$ / $\\mathit{{144}}$ ($\\mathit{{{zero_ratio:.1f}\\%}}$)"
    )
    ax.text(0.025, 0.60, text_summary, transform=ax.transAxes,
            bbox=dict(boxstyle='square,pad=0.5', facecolor='#FFFFFF', edgecolor='#000000', lw=0.9),
            fontsize=9.0, family='Times New Roman')
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=600)
    plt.close()
    print(f"[SUCCESS] Figure 1 saved to {save_path}")

# ==============================================================================
# FIGURE 2: BESS BI-DIRECTIONAL DIVERGING ENERGY BALANCE & TERMINAL CLOSURE
# ==============================================================================
def plot_figure_2(save_path="Figure2_BESS_Energy_Balance_Diverging.png"):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.5, 4.0), dpi=600,
                                   gridspec_kw={'width_ratios': [3.5, 1.2]})
    
    x = np.arange(len(bess_periods))
    bar_width = 0.52
    
    # --- Subplot 1: Bi-directional Diverging Bar Chart (Charge > 0, Discharge < 0) ---
    bars_chg = ax1.bar(x, charge_kwh, width=bar_width, color=COLOR_CHG, edgecolor='#000000',
                       lw=1.0, label="Charging Energy $E_{\\mathrm{ch}}$ (+)")
    bars_dis = ax1.bar(x, -discharge_kwh, width=bar_width, color=COLOR_DIS, edgecolor='#000000',
                       lw=1.0, label="Discharging Energy $E_{\\mathrm{dis}}$ (−)")
    
    # Neutral zero line
    ax1.axhline(0, color='#000000', lw=1.2)
    
    # Explicit italic numeric data callouts on bars
    for bar in bars_chg:
        height = bar.get_height()
        if height > 400:
            ax1.text(bar.get_x() + bar.get_width()/2.0, height + 150,
                     f"$\\mathit{{{height:.1f}}}$", ha='center', va='bottom',
                     fontsize=8.5, family='Times New Roman')
    for bar in bars_dis:
        height = bar.get_height()
        if abs(height) > 400:
            ax1.text(bar.get_x() + bar.get_width()/2.0, height - 200,
                     f"$\\mathit{{{abs(height):.1f}}}$", ha='center', va='top',
                     fontsize=8.5, family='Times New Roman')
            
    ax1.set_xticks(x)
    ax1.set_xticklabels(bess_periods, rotation=18, ha='right')
    ax1.set_ylim(-7500, 7000)
    ax1.yaxis.set_major_formatter(num_fmt)
    ax1.set_ylabel("Aggregated Energy (kWh / 4-Hour Window)", fontweight='bold', labelpad=6)
    ax1.set_title("(a) Bi-directional Storage Dispatch Dynamics", loc='left', fontweight='bold', pad=8)
    ax1.grid(True, linestyle=":", axis='y', alpha=0.5)
    ax1.legend(loc="upper left", frameon=True, edgecolor='#000000', framealpha=1.0)
    
    # --- Subplot 2: Boundary State of Charge (SoC) Loop Conservation ---
    soc_points = [soc_initial_kwh, soc_terminal_kwh]
    soc_labels = ["0:00 Initial", "24:00 Terminal"]
    x_soc = np.arange(2)
    
    bars_soc = ax2.bar(x_soc, soc_points, width=0.45, color=COLOR_SOC,
                       edgecolor='#000000', lw=1.0)
    
    # Benchmark dashed reference line
    ax2.axhline(6000.0, color='#000000', linestyle='--', lw=1.0)
    for bar in bars_soc:
        h = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2.0, h + 150,
                 f"$\\mathit{{{h:.1f}}}$", ha='center', va='bottom',
                 fontsize=8.5, family='Times New Roman')
                 
    ax2.set_xticks(x_soc)
    ax2.set_xticklabels(soc_labels, rotation=18, ha='right')
    ax2.set_ylim(0, 8000)
    ax2.yaxis.set_major_formatter(num_fmt)
    ax2.set_ylabel("Storage Content (kWh)", fontweight='bold', labelpad=4)
    ax2.set_title("(b) State Conservation", loc='left', fontweight='bold', pad=8)
    ax2.grid(True, linestyle=":", axis='y', alpha=0.5)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=600)
    plt.close()
    print(f"[SUCCESS] Figure 2 saved to {save_path}")

# ==============================================================================
# FIGURE 3: 24-HOUR POLAR PHASE CLOCK & EMPIRICAL CUMULATIVE DISTRIBUTION
# ==============================================================================
def plot_figure_3(save_path="Figure3_Polar_Phase_and_Cumulative_Spectrum.png"):
    fig = plt.figure(figsize=(9.0, 4.2), dpi=600)
    
    # --- Left Subplot: 24-Hour Polar Clock Phase Diagram ---
    ax_polar = fig.add_subplot(1, 2, 1, projection='polar')
    
    theta = np.linspace(0, 2 * np.pi, 144, endpoint=False)
    # Align 0:00 to the top (North), clockwise rotation matching a 24-hour clock
    ax_polar.set_theta_direction(-1)
    ax_polar.set_theta_offset(np.pi / 2.0)
    
    # Polar bars strictly representing purchase energy intensity
    width = (2 * np.pi) / 144.0
    
    # Normalizing colormap (Batlow / Muted Cividis)
    norm = mpl.colors.Normalize(vmin=0, vmax=np.max(grid_purchase_kwh))
    cmap = mpl.cm.cividis
    colors = cmap(norm(grid_purchase_kwh))
    
    bars = ax_polar.bar(theta, grid_purchase_kwh, width=width, bottom=150.0,
                        color=colors, edgecolor='none', alpha=0.92)
    
    # Polar labels for 24-hour cycle
    clock_ticks = np.linspace(0, 2 * np.pi, 8, endpoint=False)
    clock_labels = [f"$\\mathit{{{h}:00}}$" for h in [0, 3, 6, 9, 12, 15, 18, 21]]
    ax_polar.set_xticks(clock_ticks)
    ax_polar.set_xticklabels(clock_labels, fontsize=9.0)
    ax_polar.yaxis.set_major_formatter(num_fmt)
    ax_polar.set_rlabel_position(75)
    ax_polar.set_title("(a) Diurnal Circular Phase Rhythm", loc='left', fontweight='bold', pad=14)
    
    # --- Right Subplot: Empirical Cumulative Distribution Function (ECDF) ---
    ax_ecdf = fig.add_subplot(1, 2, 2)
    
    sorted_purchase = np.sort(grid_purchase_kwh)
    ecdf = np.arange(1, len(sorted_purchase) + 1) / float(len(sorted_purchase))
    
    ax_ecdf.step(sorted_purchase, ecdf, where='post', color=COLOR_GRID, lw=1.8,
                 label="Empirical Cumulative Probability")
    ax_ecdf.scatter([0.0], [np.mean(sorted_purchase == 0.0)], color=COLOR_ACCENT,
                    s=40, zorder=5, edgecolors='black', lw=0.8)
    
    zero_pct = (np.sum(sorted_purchase == 0.0) / 144.0)
    ax_ecdf.annotate(f"Zero Grid Purchase Fraction:\n$\\mathit{{{zero_pct*100:.1f}\\%}}$ ($\\mathit{{58}}$ intervals)",
                     xy=(0.0, zero_pct), xytext=(180, 0.25),
                     arrowprops=dict(arrowstyle="->", color="black", lw=0.9),
                     fontsize=9.0, family='Times New Roman')
                     
    ax_ecdf.set_xlim(-20, 1550)
    ax_ecdf.set_ylim(0, 1.05)
    ax_ecdf.xaxis.set_major_formatter(num_fmt)
    ax_ecdf.yaxis.set_major_formatter(num_fmt)
    ax_ecdf.set_xlabel("Energy Purchase Magnitude $Q_{\\mathrm{grid}}$ (kWh)", fontweight='bold', labelpad=6)
    ax_ecdf.set_ylabel("Empirical Cumulative Probability $F(x)$", fontweight='bold', labelpad=6)
    ax_ecdf.set_title("(b) Procurement Intensity Distribution", loc='left', fontweight='bold', pad=8)
    ax_ecdf.grid(True, linestyle=":", alpha=0.5)
    ax_ecdf.legend(loc="lower right", frameon=True, edgecolor='#000000', framealpha=1.0)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=600)
    plt.close()
    print(f"[SUCCESS] Figure 3 saved to {save_path}")

# ==============================================================================
# MAIN EXECUTION ENTRY POINT
# ==============================================================================
if __name__ == "__main__":
    import os
    # 确保根目录下的 figures 文件夹存在
    os.makedirs("figures", exist_ok=True)
    
    print("==================================================================")
    print("Generating Publication-Grade Figures for Q1 Analysis...")
    print("==================================================================")
    # 图片统一输出到 figures/ 目录，保持根目录整洁
    plot_figure_1("figures/Figure1_Diurnal_Grid_Procurement_Profile.png")
    plot_figure_2("figures/Figure2_BESS_Energy_Balance_Diverging.png")
    plot_figure_3("figures/Figure3_Polar_Phase_and_Cumulative_Spectrum.png")
    print("==================================================================")
    print("All figures successfully rendered at 600 DPI into figures/ folder.")
    print("==================================================================")