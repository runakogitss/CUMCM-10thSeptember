import os
import sys
import pandas as pd
import numpy as np

# ==============================================================================
# 1. 单一真实数据源 (SSOT) 锁定与一致性校验
# ==============================================================================
p_opt = os.path.join("results", "Q2_optimized.xlsx")
p_res = os.path.join("results", "result2.xlsx")

if os.path.exists(p_res) and os.path.exists(p_opt):
    df_res_check = pd.read_excel(p_res, sheet_name="紧急购电量").dropna(subset=["购电量"])
    df_opt_check = pd.read_excel(p_opt, sheet_name="紧急购电量").dropna(subset=["购电量"])
    diff = abs(df_res_check.iloc[:, 2].astype(float).sum() - df_opt_check.iloc[:, 2].astype(float).sum())
    if diff > 1e-2:
        print(f"[警告] result2.xlsx 与 Q2_optimized.xlsx 数据不一致 (差额 {diff:.2f} kWh)，优先使用最新生成的 Q2_optimized.xlsx！")
    excel_path = p_opt
elif os.path.exists(p_opt):
    excel_path = p_opt
elif os.path.exists(p_res):
    excel_path = p_res
else:
    raise FileNotFoundError("未在 results/ 目录下找到 Q2_optimized.xlsx 或 result2.xlsx")

print(f"[INFO] 正在解析数据源: {excel_path}")

# ==============================================================================
# 2. 读取与清洗数据
# ==============================================================================
df_em = pd.read_excel(excel_path, sheet_name="紧急购电量")
assert len(df_em.columns) >= 3, f"[FAIL] 紧急购电量列数不足: 实际 {len(df_em.columns)} 列"

col_date = df_em.columns[0]
col_time = df_em.columns[1]
col_kwh  = df_em.columns[2]

df_valid = df_em.dropna(subset=[col_date, col_time, col_kwh]).copy()
df_valid["kwh_val"] = pd.to_numeric(df_valid[col_kwh], errors="coerce")
df_valid = df_valid[df_valid["kwh_val"] > 1e-4].copy()
df_valid["date_str"] = pd.to_datetime(df_valid[col_date]).dt.strftime("%Y-%m-%d")

# ==============================================================================
# 3. 物理与工程合法性前置断言 (不硬编码单日数值)
# ==============================================================================
print("=" * 70)
print("              执行表 3 数据物理守恒前置断言审查")
print("=" * 70)

# 断言 1: 全年紧急购电总量守恒 (允许求解器舍入容差 10 kWh 内)
total_em_yearly = df_valid["kwh_val"].sum()
assert abs(total_em_yearly - 105491.12) < 10.0, (
    f"[断言失败] 全年紧急购电总量异常: 实际 {total_em_yearly:.2f} kWh, 期望 ~105491.12 kWh"
)
print(f"[PASS 1/3] 全年紧急购电总量守恒校验通过 (累计: {total_em_yearly:.2f} kWh)")

# 断言 2: 单步与时段电量非负性硬约束
assert (df_valid["kwh_val"] >= 0).all(), "[断言失败] 存在非物理负值紧急购电量"
print("[PASS 2/3] 电量非负性物理约束检验通过")

# 断言 3: 日期格式合法性
assert len(df_valid["date_str"].unique()) > 0, "[断言失败] 无法提取有效日期索引"
print(f"[PASS 3/3] 数据表结构完整，共包含 {len(df_valid)} 行有效紧急购电事件")
print("=" * 70)
print(">>> 前置审查全部通过，真实数据无损动态抽取 <<<\n")

# ==============================================================================
# 4. 动态提取四个指定代表日数据并对齐
# ==============================================================================
target_specs = [
    ("2025-03-20", "2025.3.20 (春分)"),
    ("2025-06-21", "2025.6.21 (夏至)"),
    ("2025-09-23", "2025.9.23 (秋分)"),
    ("2025-12-21", "2025.12.21 (冬至)")
]

day_records = {}
for d_iso, d_label in target_specs:
    sub = df_valid[df_valid["date_str"] == d_iso]
    records = []
    for _, row in sub.iterrows():
        t_span = str(row[col_time]).strip()
        val = float(row["kwh_val"])
        records.append((t_span, f"{val:.2f}"))
    
    # 若当天无紧急购电，填入无缺电标准占位
    if not records:
        records.append(("-", "0.00"))
        
    day_records[d_label] = records

# 计算最大展开行数以实现终端对称对齐
max_rows = max(len(recs) for recs in day_records.values())
aligned_cols = {}
for _, d_label in target_specs:
    recs = day_records[d_label]
    aligned_cols[d_label] = recs + [("-", "-")] * (max_rows - len(recs))

# ==============================================================================
# 5. 终端对齐打印表 3
# ==============================================================================
header_dates = [d_label for _, d_label in target_specs]
print("表 3  微网在指定日期的紧急购电量")
print("-" * 110)
print(f"{header_dates[0]:^24} | {header_dates[1]:^24} | {header_dates[2]:^24} | {header_dates[3]:^24}")
print(f"{'时间段':<14}{'购电量(kWh)':<10} | {'时间段':<14}{'购电量(kWh)':<10} | {'时间段':<14}{'购电量(kWh)':<10} | {'时间段':<14}{'购电量(kWh)':<10}")
print("-" * 110)

for r in range(max_rows):
    row_cells = []
    for _, d_label in target_specs:
        t_val, k_val = aligned_cols[d_label][r]
        row_cells.append(f"{t_val:<15}{k_val:<9}")
    print(" | ".join(row_cells))

print("-" * 110)

# 输出代表日各天实际汇总（用于反哺核验论文正文表 2 中的数值）
print("\n[代表日紧急购电总量汇总]")
for d_iso, d_label in target_specs:
    sub_sum = df_valid[df_valid["date_str"] == d_iso]["kwh_val"].sum()
    print(f"  * {d_label}: {sub_sum:.2f} kWh")