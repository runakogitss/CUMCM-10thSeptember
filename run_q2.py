import os
import pandas as pd

from src.data_loader import (
    load_annex1_tariffs,
    load_annex2_actuals,
)
from src.simulator_q2 import (
    run_q2_simulation,
    run_q2_baseline_simulation,
)
from src.export_tools import (
    export_q2_result,
    verify_q2_export,
    RESULTS_DIR,
)


def main():
    # 1. 载入官方基准数据
    tariffs = load_annex1_tariffs()
    load_act, pv_act = load_annex2_actuals()

    # 2. 启发式规则基线 (含 1 月自然预热)
    print("Running baseline Q2 (passive buffer, with Jan warm-up)...")
    res_base = run_q2_baseline_simulation(tariffs, load_act, pv_act)

    # 3. 两阶段鲁棒优化策略 (含 1 月自然预热)
    print("Running two-stage robust & arbitrage Q2 (with Jan warm-up)...")
    res_opt = run_q2_simulation(tariffs, load_act, pv_act)

    # 4. 导出官方 result2.xlsx
    out_xlsx = export_q2_result(res_opt)

    # 5. 格式与数值健康审查
    verify_q2_export(
        out_xlsx,
        res_opt["total_em_kwh"],
        res_opt["total_cost"],
    )

    # 6. 经济性指标汇总并打印
    baseline_cost = float(res_base["total_cost"])
    opt_cost = float(res_opt["total_cost"])
    savings = baseline_cost - opt_cost
    savings_pct = 100.0 * savings / baseline_cost

    summary_rows = [
        ("Baseline Q2 Cost (Yuan)", round(baseline_cost, 2)),
        ("Two-Stage Optimized Q2 Cost (Yuan)", round(opt_cost, 2)),
        ("Cost Reduction (Yuan)", round(savings, 2)),
        ("Cost Reduction (%)", round(savings_pct, 2)),
        ("Total Day-Ahead Planned Energy (kWh)", round(res_opt["total_plan_kwh"], 2)),
        ("Total Emergency Purchase Volume (kWh)", round(res_opt["total_em_kwh"], 2)),
        ("Emergency Penalty Cost (Yuan)", round(res_opt["total_emergency_cost"], 2)),
        ("Baseline Warm-up End SOC at Jan 31 24:00 (kWh)", round(float(res_base["warmup_end_soc"]), 2)),
        ("Optimized Warm-up End SOC at Jan 31 24:00 (kWh)", round(float(res_opt["warmup_end_soc"]), 2)),
    ]

    summary_df = pd.DataFrame(summary_rows, columns=["Metric", "Value"])
    print("\n=== Q2 Verification: Baseline vs Two-Stage Optimized ===")
    print(summary_df.to_string(index=False))


if __name__ == "__main__":
    main()