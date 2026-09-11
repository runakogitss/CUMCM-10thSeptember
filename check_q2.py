import numpy as np
import pandas as pd

excel_path = "results/Q2_optimized.xlsx"

print("=" * 60)
print("     CUMCM 2026 Q2 Deliverables Comprehensive Audit")
print("=" * 60)

# 1. 计划购电量 (Sheet 1)
df_p = pd.read_excel(excel_path, sheet_name="计划购电量")
print(f"Sheet 1 [计划购电量] 维度: {df_p.shape} (行数 x 列数)")
print(f"  - 天数行数: {len(df_p)} 天 -> {'PASS (334天全覆盖)' if len(df_p) == 334 else 'CHECK'}")
# 提取所有时步数值（排除首列日期与末尾全天合计列）
numeric_cols = df_p.select_dtypes(include=[np.number])
print(f"  - 数值列数量: {numeric_cols.shape[1]} (包含 144 时步 + 汇总列)")
total_plan_grid = numeric_cols.iloc[:, -2].sum() if numeric_cols.shape[1] >= 146 else numeric_cols.sum().sum()
print(f"  - 全年计划购电总量: {total_plan_grid:,.2f} kWh")

# 2. 充放电量 (Sheet 2)
df_b = pd.read_excel(excel_path, sheet_name="充放电量")
print(f"\nSheet 2 [充放电量] 维度: {df_b.shape} (行数 x 列数)")
print(f"  - 时段行数: {len(df_b)} 行 -> {'PASS (334天 x 6时段 = 2004)' if len(df_b) == 2004 else 'CHECK'}")
print("  - 列名列表:", list(df_b.columns))

# 3. 紧急购电量 (Sheet 3)
df_e = pd.read_excel(excel_path, sheet_name="紧急购电量")
print(f"\nSheet 3 [紧急购电量] 维度: {df_e.shape} (行数 x 列数)")
print(f"  - 紧急购电触发时段记录数: {len(df_e)} 段")
if len(df_e) > 0:
    # 最后一列通常为紧急购电量(kWh)
    em_kwh_total = df_e.iloc[:, -1].sum()
    print(f"  - 全年紧急购电总量: {em_kwh_total:,.2f} kWh (预期 ~105,491.12 kWh)")
else:
    print("  - 无紧急购电记录")

print("=" * 60)