# 问题 1：确定性日日前购电策略数学模型说明书
# Technical Specification & Mathematical Formulation: Question 1

---

## Part 1: 中文建模正文（供论文手撰写与排版）

### 1.1 系统描述与合理假设
微网系统由分布式光伏阵列、集中式储能系统（BESS）、小区负荷以及与外部电网连接的变压母线组成。针对问题 1 的静态日日前调度场景，建立如下基本假设：
1. **单向馈电假设**：微网定位于分布式就地消纳，不具备倒送电网逆向计量条件，外部电网购电量满足 $P_{\text{grid}}(t) \ge 0$。
2. **集总参数与线损忽略**：小区内部供电半径较小，忽略微网母线潮流阻抗损耗与变流器无功波动。
3. **稳态时步假设**：在每个离散时间段 $\Delta t = 10\text{ min} = 1/6\text{ h}$ 内，电价、负荷功率与光伏发电功率均保持稳态恒定。
4. **恒定充放电效率**：储能充放电单向等效转换效率恒定为 $\eta = 0.90$，忽略环境温度与充放电倍率对容量衰减的影响。

---

### 1.2 符号系统定义

| 符号 | 物理含义 | 单位 / 维度 | 属性 |
| :--- | :--- | :--- | :--- |
| $\mathcal{T}$ | 调度时步离散集合，$\mathcal{T} = \{1, 2, \dots, 144\}$ | 无量纲集合 | 索引集合 |
| $\Delta t$ | 决策步长，$\Delta t = 1/6$ | $\text{h}$ | 系统常数 |
| $c(t)$ | $t$ 时段外部电网购电单价 | 元/$\text{kWh}$ | 已知参数 (附件 1) |
| $P_{\text{load}}(t)$ | $t$ 时段小区用电负荷功率 | $\text{kW}$ | 已知参数 (附件 1) |
| $P_{\text{pv}}(t)$ | $t$ 时段分布式光伏预测发电功率 | $\text{kW}$ | 已知参数 (附件 1) |
| $E_{\max}$ | 储能系统最大额定物理容量 ($12000$) | $\text{kWh}$ | 物理常数 (附录 1) |
| $E_{\min}, E_{\max}'$ | 储能安全允许荷电区间 $[1200, 10800]$ (10%–90% SoC) | $\text{kWh}$ | 物理常数 (附录 1) |
| $P_{\text{ch}}^{\max}, P_{\text{dis}}^{\max}$ | 储能充放电变流器功率硬上限 ($5000$) | $\text{kW}$ | 物理常数 (附录 1) |
| $\eta$ | 储能系统单向充放电效率 ($0.90$) | 无量纲标量 | 物理常数 (附录 1) |
| $E(0)$ | 调度周期起始储电量 ($6000$) | $\text{kWh}$ | 状态初值 (附录 1) |
| $P_{\text{grid}}(t)$ | $t$ 时段向外部电网申请的计划购电功率 | $\text{kW}$ | **连续决策变量** |
| $P_{\text{ch}}(t)$ | $t$ 时段储能系统的充电功率 | $\text{kW}$ | **连续决策变量** |
| $P_{\text{dis}}(t)$ | $t$ 时段储能系统的放电功率 | $\text{kW}$ | **连续决策变量** |
| $P_{\text{curt}}(t)$ | $t$ 时段光伏弃电松弛功率 (确保凸可行域) | $\text{kW}$ | **连续松弛变量** |
| $E(t)$ | $t$ 时段末储能系统的储电量 | $\text{kWh}$ | **连续状态变量** |

---

### 1.3 线性规划（LP）模型构建

#### 目标函数
在满足小区用电安全与设备运行物理约束的前提下，最小化全天计划购电总费用：
$$\min Z_1 = \sum_{t=1}^{144} c(t) \cdot P_{\text{grid}}(t) \cdot \Delta t$$

#### 约束条件
1. **微网功率供需平衡约束**：
   微网提供的电能不可低于小区负载，允许在光伏极大且电池充满时产生极少量必要弃光：
   $$P_{\text{grid}}(t) + P_{\text{pv}}(t) - P_{\text{curt}}(t) + P_{\text{dis}}(t) - P_{\text{ch}}(t) = P_{\text{load}}(t), \quad \forall t \in \mathcal{T}$$
   $$P_{\text{grid}}(t) \ge 0, \quad P_{\text{curt}}(t) \ge 0, \quad \forall t \in \mathcal{T}$$

2. **储能荷电状态（SoC）时序动态演化方程**：
   考虑充放电单向能量折损，状态递推方程满足：
   $$E(t) = E(t-1) + \eta P_{\text{ch}}(t) \Delta t - \frac{1}{\eta} P_{\text{dis}}(t) \Delta t, \quad \forall t \in \mathcal{T}$$

3. **变流器功率与储能安全运行边界**：
   $$0 \le P_{\text{ch}}(t) \le 5000, \quad \forall t \in \mathcal{T}$$
   $$0 \le P_{\text{dis}}(t) \le 5000, \quad \forall t \in \mathcal{T}$$
   $$1200 \le E(t) \le 10800, \quad \forall t \in \mathcal{T}$$

4. **日末能量守恒与闭环运行约束**：
   题目严格要求 0:00 与 24:00 储电量相同：
   $$E(144) = E(0) = 6000\text{ kWh}$$

---

### 1.4 充放电互斥性松弛定理与数学证明
**定理**：由于外部电网购电价格 $c(t) > 0$，且储能转换效率 $\eta = 0.90 < 1$，上述模型在最优解处必然自动满足互斥充放电特性：
$$P_{\text{ch}}^*(t) \cdot P_{\text{dis}}^*(t) = 0, \quad \forall t \in \mathcal{T}$$
无需引入计算复杂度极高的 0-1 整数状态变量，模型可作为标准连续线性规划（LP）在多项式时间内精确求解。

**证明过程（反证法）**：
设模型存在一个可行解，在时段 $t$ 存在同时充放电现象，即 $P_{\text{ch}}^*(t) > 0$ 且 $P_{\text{dis}}^*(t) > 0$。
构造公共充放抵消量 $\delta = \min(P_{\text{ch}}^*(t), P_{\text{dis}}^*(t)) > 0$。
构建构造解：
$$P_{\text{ch}}'(t) = P_{\text{ch}}^*(t) - \delta \ge 0, \quad P_{\text{dis}}'(t) = P_{\text{dis}}^*(t) - \delta \ge 0$$
* 检验功率平衡：
  $$P_{\text{dis}}'(t) - P_{\text{ch}}'(t) = (P_{\text{dis}}^*(t) - \delta) - (P_{\text{ch}}^*(t) - \delta) = P_{\text{dis}}^*(t) - P_{\text{ch}}^*(t)$$
  微网对外部电网的购电量 $P_{\text{grid}}^*(t)$ 及弃光量保持完全不变，目标函数值保持不变。
* 检验该时步储电量增量变动：
  $$\Delta E'(t) - \Delta E^*(t) = \left[ \eta(P_{\text{ch}}^* - \delta) - \frac{1}{\eta}(P_{\text{dis}}^* - \delta) \right]\Delta t - \left[ \eta P_{\text{ch}}^* - \frac{1}{\eta} P_{\text{dis}}^* \right]\Delta t$$
  $$\Delta E'(t) - \Delta E^*(t) = \delta \Delta t \left( \frac{1}{\eta} - \eta \right) = \delta \Delta t \left( \frac{1 - \eta^2}{\eta} \right)$$
  因 $\eta = 0.90$，$\frac{1 - 0.9^2}{0.9} = \frac{0.19}{0.9} \approx 0.211 > 0$。
  消除无意义的对充对放后，储能系统以完全相同的外部购电成本，获得了更高的日末剩余电量，或者可以在日内高电价时段减少外部购电，因此原解不可能为最小化费用的最优解。
  证毕。

---

### 1.5 论文成果填报模板（表 1 与 表 2）

#### 表 1 微网在指定时间段的购电量及全天的购电量和购电费
| 时间段 | 购电量 (kWh) | 时间段 | 购电量 (kWh) | 时间段 | 购电量 (kWh) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| 10:00-10:10 | [待填入] | 12:00-12:10 | [待填入] | 14:00-14:10 | [待填入] |
| 16:00-16:10 | [待填入] | 18:00-18:10 | [待填入] | 20:00-20:10 | [待填入] |
| **全天购电量 (kWh)** | **[待填入]** | **全天购电费 (元)** | **[待填入]** | — | — |

#### 表 2 储能设备在指定时间段的充放电量及 0:00 和 24:00 的储电量
| 时间段 | 充电量 (kWh) | 放电量 (kWh) | 时间段 | 充电量 (kWh) | 放电量 (kWh) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| 0:00-4:00 | [待填入] | [待填入] | 4:00-8:00 | [待填入] | [待填入] |
| 8:00-12:00 | [待填入] | [待填入] | 12:00-16:00 | [待填入] | [待填入] |
| 16:00-20:00 | [待填入] | [待填入] | 20:00-24:00 | [待填入] | [待填入] |
| **0:00 储电量 (kWh)** | **6000.00** | **24:00 储电量 (kWh)** | **6000.00** | — | — |

---

## Part 2: Technical Directives for Programmer (`solver_q1.py`)

1. **Input Source**: Strictly load `Annex1.xlsx` via `src.utils.data_loader`. Do NOT touch `Annex2.xlsx` for Q1.
2. **Variable Vector Layout per time step $t \in [0, 143]$**:
   - `x[5*t + 0]`: $P_{\text{grid}}(t) \ge 0$ (kW)
   - `x[5*t + 1]`: $P_{\text{curt}}(t) \ge 0$ (kW, Solar curtailment slack)
   - `x[5*t + 2]`: $P_{\text{ch}}(t) \in [0, 5000]$ (kW)
   - `x[5*t + 3]`: $P_{\text{dis}}(t) \in [0, 5000]$ (kW)
   - `x[5*t + 4]`: $E(t) \in [1200, 10800]$ (kWh)
3. **Mandatory Hard Constraints in `A_eq`**:
   - Initial condition at $t=0$: $E(0) = 6000\text{ kWh}$.
   - Terminal circular constraint at $t=143$ (24:00): $E(143) = 6000\text{ kWh}$.
4. **Annex 5 Unit Conversion & Export**:
   - Convert optimized power variables (kW) to energy (kWh): $\text{Energy\_kWh} = \text{Power\_kW} \times \frac{1}{6}$.
   - Maintain pre-existing sheet structures in `Annex5_Templates/result1.xlsx`:
     - Sheet 1: `计划购电量` (144 rows, 10-minute steps).
     - Sheet 2: `充放电量` (6 aggregated 4-hour windows, row 8 has 0:00 & 24:00 SoC).