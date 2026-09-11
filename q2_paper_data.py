import pandas as pd
import numpy as np

excel_path = "results/Q2_optimized.xlsx"

# 1. 加载三个 Sheet
df_plan = pd.read_excel(excel_path, sheet_name="计划购电量")
df_bess = pd.read_excel(excel_path, sheet_name="充放电量")
df_em   = pd.read_excel(excel_path, sheet_name="紧急购电量")

# 2. 提取四季指定代表日
target_dates = ["2025-03-20", "2025-06-21", "2025-09-23", "2025-12-21"]
date_names = ["春分 (3.20)", "夏至 (6.21)", "秋分 (9.23)", "冬至 (12.21)"]

# 格式化日期匹配
df_plan["日期_str"] = pd.to_datetime(df_plan.iloc[:, 0]).dt.strftime("%Y-%m-%d")
df_bess["日期_ffill"] = pd.to_datetime(df_bess.iloc[:, 0]).ffill().dt.strftime("%Y-%m-%d")
df_em_clean = df_em.dropna(subset=["购电时间段", "购电量"]).copy()
df_em_clean["日期_str"] = pd.to_datetime(df_em_clean.iloc[:, 0]).dt.strftime("%Y-%m-%d")

print("\n" + "="*80)
print("【可直接复制给 AI 的 Q2 论文手素材 - 四季代表日切片数据】")
print("="*80)
print("| 代表日 | 全天计划购电量 (kWh) | 全天充电量 (kWh) | 全天放电量 (kWh) | 0:00 初始储电 (kWh) | 24:00 终止储电 (kWh) | 紧急购电量 (kWh) |")
print("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |")

for d_str, d_name in zip(target_dates, date_names):
    # 计划购电量 (第 146 列为全天购电量)
    p_row = df_plan[df_plan["日期_str"] == d_str]
    p_total = p_row.iloc[0, -2] if len(p_row) > 0 else 0.0
    
    # 充放电量及首末状态
    b_rows = df_bess[df_bess["日期_ffill"] == d_str]
    chg_total = b_rows.iloc[:, 2].sum() if len(b_rows) > 0 else 0.0
    dis_total = b_rows.iloc[:, 3].sum() if len(b_rows) > 0 else 0.0
    soc_0 = b_rows.iloc[0, 5] if len(b_rows) > 0 else 0.0
    soc_24 = b_rows.iloc[1, 5] if len(b_rows) > 0 else 0.0
    
    # 紧急购电量
    e_rows = df_em_clean[df_em_clean["日期_str"] == d_str]
    em_total = e_rows.iloc[:, 2].sum() if len(e_rows) > 0 else 0.0
    
    print(f"| {d_name} | {p_total:.2f} | {chg_total:.2f} | {dis_total:.2f} | {soc_0:.2f} | {soc_24:.2f} | {em_total:.2f} |")

print("="*80)