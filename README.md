# CUMCM 2026 Problem C: Microgrid and External Grid Power Dispatch Strategy Strategy Guide & Technical Specification

This README serves as a comprehensive briefing, technical blueprint, and task distribution plan for the CUMCM 2026 Problem C competition. It is structured for direct integration into an AI-driven development environment to guide modeling, programming, and paper writing.

---

## 1. Project Overview & Strategy

* **Problem Domain:** Classic Microgrid Energy Management & Rolling Horizon Operations Research / Power Systems Optimization.


* **Core Advantage:** High mathematical determinism and global optimality using Linear Programming (LP), Mixed-Integer Linear Programming (MILP), and Model Predictive Control (MPC) without high-risk external online system integrations.


* **Key Objective:** Minimize total grid power purchase costs (including base purchases, variance surcharges, and emergency penalties) while maintaining power balance and respecting Battery Energy Storage System (BESS) constraints.



---

## 2. System Constants & Operational Parameters (Appendix 1)

* **Sampling Horizon:** $\Delta t = 10\text{ min} = \frac{1}{6}\text{ h}$ ($T = 144$ time-steps per 24-hour cycle).


* **BESS Limits:**
* **Capacity Rating:** $E_{\max} = 12000\text{ kWh}$.


* **Safe SOC Operating Band:** $E(t) \in [1200, 10800]\text{ kWh}$ ($10\%$ to $90\%$ SOC).


* **Max Power Limits:** $P_{\text{ch}}^{\max} = 5000\text{ kW}$, $P_{\text{dis}}^{\max} = 5000\text{ kW}$.


* **Round-Trip Efficiency:** $\eta = 0.90$ ($90\%$ efficiency: charging efficiency $\eta$, discharging efficiency $\frac{1}{\eta}$).


* **Initial Energy State (2025-01-01 00:00):** $E(0) = 6000\text{ kWh}$.





---

## 3. Mathematical Formulations & Question Breakdown

### Question 1: Deterministic Day-Ahead Linear Programming (LP)

* **Given Inputs:** Constant/known daily time-of-use electricity price $c(t)$, deterministic load profile $P_{\text{load}}(t)$, and PV forecast $P_{\text{pv}}(t)$ from Annex 1.


* **Decision Variables ($t = 1, \dots, 144$):**
* $P_{\text{grid}}(t) \ge 0$: Grid power purchase (kW).


* $P_{\text{ch}}(t) \in [0, 5000]$: Battery charging power (kW).


* $P_{\text{dis}}(t) \in [0, 5000]$: Battery discharging power (kW).


* $E(t) \in [1200, 10800]$: Battery state at interval end (kWh).




* **Objective:**

$$\min \sum_{t=1}^{144} c(t) \cdot P_{\text{grid}}(t) \cdot \Delta t$$



* **Subject to Constraints:**
1. *Power Balance:*

$$P_{\text{grid}}(t) + P_{\text{pv}}(t) + P_{\text{dis}}(t) - P_{\text{ch}}(t) \ge P_{\text{load}}(t), \quad \forall t \in [1, 144]$$



2. *BESS Dynamics:*

$$E(t) = E(t-1) + \eta P_{\text{ch}}(t)\Delta t - \frac{1}{\eta}P_{\text{dis}}(t)\Delta t, \quad \forall t \in [1, 144]$$



3. *Boundary Condition:*

$$E(144) = E(0) = 6000\text{ kWh}$$





* **Linearity Property:** Because $\eta = 0.9 < 1$ and $c(t) > 0$, simultaneous charging and discharging is sub-optimal; pure continuous LP automatically ensures mutual exclusivity without binary variables.



---

### Question 2: Day-Ahead Planning Under Uncertainty & 5x Emergency Penalty

* **Context:** Actual daily load $P_{\text{load}}^{\text{act}}(t)$ and solar generation $P_{\text{pv}}^{\text{act}}(t)$ for 2025 are given in Attachment 2. Outputs are required for Feb 1 to Dec 31, 2025 (January serves as prior training data).


* **Penalty Logic:** Day-ahead baseline commitment $P_{\text{plan}}(t)$ is fixed at 0:00. If real-time demand exceeds supply, emergency power $P_{\text{em}}(t)$ is purchased at $5 \times c(t)$.


* **Objective Cost Model:**

$$C_{\text{total}} = \sum_{t} \left[ c(t)P_{\text{plan}}(t)\Delta t + 5c(t)P_{\text{em}}(t)\Delta t \right]$$



* **Optimization Insights:**
* Treat this as an Asymmetric Loss / Newsvendor Formulation with critical ratio $\alpha = \frac{5-1}{5} = 0.8$.


* Incorporate a safety buffer/quantile adjustment during the 0:00 planning phase to minimize expensive emergency purchases.


* Maintain inter-day battery state continuity: $E_{\text{day } d}(0) = E_{\text{day } d-1}(24:00)$.





---

### Question 3: Multi-Stage Intra-Day MPC Rolling Horizon

* **Update Scheme:** Baseline plan $P_{\text{plan}}(t)$ set at 0:00. Updated 24-hour forecasts arrive at 6:00, 12:00, and 18:00 (Attachment 3), producing adjusted plans $P_{\text{adj}}(t)$.


* **Settlement Cost Structure:**
* **Baseline Cost:** $c(t)P_{\text{plan}}(t)\Delta t$

* **Over-purchase reduction:** $\Delta P^-(t) = \max(0, P_{\text{plan}}(t) - P_{\text{adj}}(t)) \Rightarrow \text{Penalty} = 0.5 \times c(t) \cdot \Delta P^-(t) \Delta t$

* **Under-purchase addition:** $\Delta P^+(t) = \max(0, P_{\text{adj}}(t) - P_{\text{plan}}(t)) \Rightarrow \text{Surcharge} = 1.5 \times c(t) \cdot \Delta P^+(t) \Delta t$

* **Unmet Emergency Deficit:** $5.0 \times c(t) \cdot P_{\text{em}}(t) \Delta t$



* **Algorithm Framework:** Formulate MPC linear sub-problems at update epochs $t \in \{0, 36, 72, 108\}$ using non-negative slack variables $\Delta P^+(t)$ and $\Delta P^-(t)$.



---

### Question 4: Dynamic Dynamic Tariffs Sensitivity

* **Modification:** Replace static time-of-use tariffs $c(t)$ with dynamic time-series matrix $c(d, t)$ from Attachment 4.


* **Execution:** Re-run the optimized pipeline built for Q2 and Q3 using dynamic pricing vectors to output `result4-2.xlsx` and `result4-3.xlsx`.



---

## 4. Repository Structure & Technical Architecture

```text
microgrid-dispatch/
├── data/
│   ├── Annex1.xlsx             # Deterministic baseline data (Q1)
│   ├── Annex2.xlsx             # Actual annual load and PV series (Q2-Q4)
│   ├── Annex3.xlsx             # Intra-day multi-period PV updates (Q3-Q4)
│   ├── Annex4.xlsx             # Real-time dynamic tariffs (Q4)
│   └── Annex5_Templates/       # Target submission format templates (.xlsx)
├── src/
│   ├── data_loader.py          # Data parsing, 10-min spline interpolation for Annex 3
│   ├── solver_q1.py            # Day-ahead deterministic LP model (PuLP / Gurobi)
│   ├── simulator_q2.py         # 334-day rolling day-ahead stochastic/robust execution
│   ├── mpc_q3.py               # 4-stage intra-day rolling horizon MPC solver
│   └── export_tools.py         # Formatter to export results to Attachment 5 templates
├── results/                    # Generated excel result files (result1.xlsx - result4-3.xlsx)
├── README.md                   # System Architecture & Task Specification
└── main.py                     # Primary pipeline execution entry point
```[cite: 3]

---

## 5. Team Roles & 72-Hour Sprint Roadmap

### Team Role Allocations

* **Modeling Lead:**
  * Formulate complete mathematical notation, sets, parameters, and matrix forms[cite: 3].
  * Derive LP relaxation proofs for battery charge/discharge mutual exclusivity[cite: 3].
  * Design quantile safety-margin policies for Q2 and MPC rolling logic for Q3[cite: 3].
  * Verify numerical consistency (e.g., energy balance, physical SOC boundaries)[cite: 3].

* **Programming Lead:**
  * Build `data_loader.py` to handle Excel IO and spline interpolation from 1-hour to 10-minute intervals[cite: 3].
  * Implement PuLP / Gurobi optimization solvers for Q1 through Q4[cite: 3].
  * Execute rolling simulations (Feb 1 – Dec 31, 2025) and verify formatting against Attachment 5[cite: 3].
  * Produce production-grade diagnostic plots (Load vs. PV vs. Grid vs. Battery SOC)[cite: 3].

* **Writing Lead:**
  * Ensure full compliance with competition formatting standards[cite: 3].
  * Structure document skeleton: Assumptions, Notation, Formulations, Sensitivity Analysis[cite: 3].
  * Typeset mathematical formulations and embed generated figures/tables[cite: 3].
  * Craft and refine the abstract to highlight key quantitative savings and dispatch strategies[cite: 3].

---

### 72-Hour Execution Roadmap


```

+-----------------------------------------------------------------------------------+
| Stage 1: Day 1 Morning                                                            |
| Target: Solve Question 1 & Setup Data Pipelines                                   |
| - Modeling: Complete Q1 LP formulation and relaxation proof.                      |
| - Coding: Build data loaders, complete Q1 solver, output result1.xlsx.            |
| - Writing: Draft Background, Assumptions, System Schematic, Notation table.       |
+-----------------------------------------------------------------------------------+
|
v
+-----------------------------------------------------------------------------------+
| Stage 2: Day 1 Evening - Day 2 Morning                                            |
| Target: Solve Question 2 (Full Year Un-Certainty Rolling Simulation)             |
| - Modeling: Derive Newsvendor critical ratio safety buffer for 5x penalty.        |
| - Coding: Build Feb-Dec simulator engine, track daily SOC continuous state.       |
| - Writing: Document Q1 figures/tables; draft Q2 mathematical model structure.     |
+-----------------------------------------------------------------------------------+
|
v
+-----------------------------------------------------------------------------------+
| Stage 3: Day 2 Afternoon - Day 2 Evening                                          |
| Target: Solve Question 3 (Multi-stage Rolling Horizon MPC)                        |
| - Modeling: Formulate multi-period deviation cost function with slack variables.  |
| - Coding: Interpolate hourly forecasts to 10-min; execute 4-stage MPC pipeline.   |
| - Writing: Analyze quantitative savings of intra-day adjustments; draw MPC chart. |
+-----------------------------------------------------------------------------------+
|
v
+-----------------------------------------------------------------------------------+
| Stage 4: Day 3 Morning                                                            |
| Target: Solve Question 4 & Conduct Sensitivity Analysis                           |
| - Modeling: Define dynamic tariff adaptation logic; design sensitivity parameters.|
| - Coding: Batch-run Q2/Q3 frameworks with dynamic price inputs; generate plots.   |
| - Writing: Complete Q3/Q4 sections; add comparison heatmaps & sensitivity analysis.|
+-----------------------------------------------------------------------------------+
|
v
+-----------------------------------------------------------------------------------+
| Stage 5: Day 3 Evening - Submission                                               |
| Target: Final Paper Polishing & Deliverable Verification                           |
| - Modeling: Summarize core quantitative metrics (cost savings, penalty reductions).|
| - Coding: Sanitize codebase, add docstrings, verify output Excel specifications.  |
| - Writing: Intensive abstract polish, full formatting check, line-by-line review. |
+-----------------------------------------------------------------------------------+

```[cite: 3]

```