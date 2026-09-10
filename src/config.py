"""
Global Configuration and Parameters for CUMCM 2026 Problem C
Microgrid & External Grid Power Dispatch Strategy
Author: Modeling Lead (feat/model-baseline)
"""

from pathlib import Path

# ==================== 项目路径导航 ====================
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
RESULTS_DIR = PROJECT_ROOT / "results"
FIGURES_DIR = PROJECT_ROOT / "figures"
PAPER_DIR = PROJECT_ROOT / "paper"

# 原始数据附件路径
ANNEX1_PATH = RAW_DATA_DIR / "Annex1.xlsx"
ANNEX2_PATH = RAW_DATA_DIR / "Annex2.xlsx"
ANNEX3_PATH = RAW_DATA_DIR / "Annex3.xlsx"
ANNEX4_PATH = RAW_DATA_DIR / "Annex4.xlsx"
TEMPLATES_DIR = RAW_DATA_DIR / "Annex5_Templates"

# 结果文件输出路径
RESULT1_PATH = RESULTS_DIR / "result1.xlsx"
RESULT2_PATH = RESULTS_DIR / "result2.xlsx"
RESULT3_PATH = RESULTS_DIR / "result3.xlsx"
RESULT4_2_PATH = RESULTS_DIR / "result4-2.xlsx"
RESULT4_3_PATH = RESULTS_DIR / "result4-3.xlsx"

# ==================== 时序离散化参数 ====================
DELTA_T = 10.0 / 60.0       # 决策步长: 10 分钟 = 1/6 小时 (h)
STEPS_PER_HOUR = 6          # 每小时 6 个离散点
STEPS_PER_DAY = 144         # 每天决策步长数 (24 * 6)

# ==================== 储能系统 (BESS) 物理参数 ====================
BATTERY_CAPACITY = 12000.0  # 额定最大容量 E_max (kWh)
SOC_MIN_ENERGY = 1200.0     # 储电量下限 (10% SoC, kWh)
SOC_MAX_ENERGY = 10800.0    # 储电量上限 (90% SoC, kWh)
MAX_CHARGE_POWER = 5000.0   # 最大充电功率 P_ch_max (kW)
MAX_DISCHARGE_POWER = 5000.0# 最大放电功率 P_dis_max (kW)
BATTERY_EFFICIENCY = 0.90   # 单向充放电效率 eta = 90%
INITIAL_ENERGY = 6000.0     # 2025-01-01 00:00 初始储电量 (kWh)

# ==================== 经济考核与违规惩罚系数 ====================
PENALTY_EMERGENCY_MULT = 5.0 # Q2/Q3: 紧急缺电采购为即时电价的 5 倍
PENALTY_OVER_PURCHASE = 0.5  # Q3: 计划购电高于调整购电（弃/退电违约扣罚 50%）
PENALTY_UNDER_PURCHASE = 1.5 # Q3: 调整购电高于计划购电（增购补差按 150% 结算）

# ==================== 论文重点展示与里程碑日期 ====================
# 表 3 指定填报的四个季节性代表日
MILESTONE_DATES = ["2025-03-20", "2025-06-21", "2025-09-23", "2025-12-21"]

# 问题 2 与问题 3 正式评测区间
EVALUATION_START_DATE = "2025-02-01"
EVALUATION_END_DATE = "2025-12-31"

# ==================== 报童模型与负荷预测超参数 ====================
# 针对 5 倍紧急购电惩罚，非对称损失报童分位数基准: (5 - 1) / 5 = 0.80
CRITICAL_QUANTILE = 0.80    
LOAD_FORECAST_WINDOW_DAYS = 7 # 历史负荷滑窗统计周期 (天)