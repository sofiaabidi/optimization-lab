# Assignment Requirements Coverage Matrix

This matrix uses the supplied Assignment 8 requirements in `plan.md` as its baseline and marks only executable or directly observed evidence as complete. `Quick` and `full` refer to repository experiment profiles; `simulator`, `classical simulation`, and `QEMU` identify the actual execution mode. Conditional course-specific additions remain pending confirmation rather than being inferred.

## A — Continuous optimization and foundations

| Requirement | Executable evidence | Status |
|---|---|---|
| Loss, regularizer, parameters, objective, gradients/backward pass; continuous/discrete, convex/nonconvex, minima and saddle examples | `src/optlab/track_a.py`; `tests/test_track_a.py`; `results/a/summary.json` | DONE — quick + full |
| GD, SGD, mini-batch SGD, Momentum, NAG, AdaGrad, RMSProp, Adam, Newton and Gauss–Newton | `run_first_order`, `run_newton`, `gauss_newton_demo`; `results/a/raw.csv`, `histories.csv` | DONE — quick + full |
| Backprop oracle and Fisher/diagonal-Hessian/HVP curvature evidence | `backpropagation_check`, `curvature_check`; focused tests; summary errors | DONE — quick + full |
| Convex/strongly-convex/nonconvex convergence and setting/noise sensitivity | `landscape_examples`; `results/a/sensitivity.csv`, `trajectories.svg` | DONE — quick + full |

## B — Discrete optimization

| Requirement | Executable evidence | Status |
|---|---|---|
| Knapsack via greedy, ILP, branch-and-bound and DP with exhaustive oracle | `src/optlab/track_b.py`; `tests/test_track_b.py`; `results/b/knapsack_raw.csv` | DONE — quick + full |
| Weighted Max-Cut exhaustive optimum, QUBO, Ising transformation and energy equivalence | `tracks/b_discrete/maxcut_instance.json`; `maxcut_qubo`, `qubo_to_ising`; `results/b/maxcut_energies.csv` | DONE — quick + full |
| Separate constraint-penalty example with feasible/infeasible penalty strengths | `cardinality_penalty_demo`; `results/b/penalty_sweep.csv` | DONE — quick + full |
| Feature selection or another additional combinatorial method, only if required by course-specific material | No supplied evidence establishes this conditional requirement | PENDING CONFIRMATION |

## C — Quantum optimization

| Requirement | Executable evidence | Status |
|---|---|---|
| Track B Max-Cut QAOA, finite shots and exhaustive classical comparison | `maxcut_hamiltonian`, `apply_qaoa`, `optimize_qaoa`; `results/c/qaoa_optimization.csv`, `qaoa_shots.csv` | DONE — CPU simulator quick + full |
| Small-Hamiltonian VQE, PQC/QNN and hybrid loop | `vqe_hamiltonian`, `optimize_vqe`, `train_qnn`; focused tests and histories | DONE — CPU simulator quick + full |
| Parameter-shift, SPSA and QNG with documented metric approximation | `parameter_shift_gradient`, `optimize_vqe`; `results/c/optimizer_comparison.csv` | DONE — CPU simulator quick + full |
| Shot cost, synthetic noise, finite-size barren-plateau illustration and embedding limitation | `qaoa_shot_experiment`, `qaoa_noise_experiment`, `barren_plateau_experiment`; raw CSVs and summary | DONE — CPU simulator quick + full; no hardware |

## D — Submodular, parallel, distributed and multi-task optimization

| Requirement | Executable evidence | Status |
|---|---|---|
| Submodular coverage, exhaustive diminishing returns, greedy/exact comparison and conditional guarantee | `coverage_value`, `verify_diminishing_returns`; focused test; `results/d/summary.json` | DONE — quick + full |
| Load balance, makespan and scheduling | `measure_scaling`, `measure_scheduling`; `parallel_scaling.csv`, `scheduling.csv` | DONE — measured local processes |
| Genuine deque-based work stealing, distinct from the shared-queue scheduling comparison | `measure_work_stealing`; exact-once/checksum test; `results/d/work_stealing.csv` | DONE — measured quick audit; 3 observed steals |
| Locality, synchronization and communication overhead | `measure_locality`, `measure_synchronization`, `measure_communication`; corresponding CSVs | DONE — measured local CPU/thread/process |
| Data, model and pipeline parallelism with actual/simulated distinction | Three demo functions; PID/equivalence test; `parallel_patterns.csv` | DONE — local processes |
| Speedup/efficiency and Amdahl/Gustafson interpretation | Measured repeats and `parallel_interpretation`; `parallel_scaling.csv` | DONE — measured + analytical interpretation |
| FedAvg vs centralized; local-step/round trade-offs | `centralized_training`, `fedavg_training`; `fedavg.csv` | DONE — sequential distributed simulation; payload analytical |
| MGDA and GradNorm vs equal weighting on a two-task model | `multitask_training`; `multitask.csv`; focused tests | DONE — quick + full |

## E — Campus EV charging

| Requirement | Executable evidence | Status |
|---|---|---|
| Explicit variables, cost objective, constraints and feasible/infeasible cases | `ChargingInstance`, `Vehicle`, `verify_schedule`; input/result CSVs | DONE — synthetic quick + full |
| First-available baseline vs cheapest-slot heuristic and exact LP | Three schedule functions; independent grid oracle; `comparison.csv` | DONE — quick + full |
| Strategy selection, cost/runtime/peak/unmet demand, scaling and sensitivity including non-improvement | README tables; `benchmark_raw.csv`, `fleet_scaling.csv`, `capacity_sensitivity.csv` | DONE — quick + full |

## F — Compiler optimization

| Requirement | Executable evidence | Status |
|---|---|---|
| Lexer/parser/AST/IR/bytecode VM and semantic equivalence | `src/optlab/track_f.py`; `tests/test_track_f.py`; `equivalence.csv` | DONE — quick + full |
| Constant folding, propagation, dead-code elimination and CSE | Four pass functions; targeted tests; `pass_effects.csv`, `ir_snapshots.json` | DONE — quick + full |
| Discrete pass-order optimization compared with a fixed order | `optimize_pass_order_dp`; `pass_order_search.csv` | DONE — exact subset DP |
| Instruction count, code size, compile/runtime and representative correctness | `benchmark.csv`, `benchmark_raw.csv`, generated-program checks | DONE — Python VM quick + full |

## G — Real xv6-riscv modification

| Requirement | Executable evidence | Status |
|---|---|---|
| Pinned upstream source, license, toolchain and reproducible patch setup | SHA `e93dabeb…`; `prepare_xv6.sh`; `patches/*.patch` | DONE — real xv6/QEMU |
| Optimized kernel scheduler feature | Strict-priority scheduler plus `setpriority`; actual kernel patch | DONE — performance policy measured under QEMU |
| Distinct scheduler accounting/diagnostic feature | Dispatch/runtime counters plus `getpstats`; accounting-stage usertests | DONE — kernel observability feature, not claimed as a second performance optimization |
| Identical CPU, mixed yield/I-O and fairness workloads, baseline vs patched | `schedbench.c`; benchmark logs, `benchmark.csv`, `comparison.csv` | DONE — QEMU quick, 3 repeats |
| Build, boot, `usertests` after each kernel change and literal diff | Three logs ending `ALL TESTS PASSED`; complete patch | DONE — real QEMU; full scaling NOT RUN |

## H — DBMS optimization

| Requirement | Executable evidence | Status |
|---|---|---|
| Seeded SQLite dataset, schema/workload, fixed settings, plans and repeated timing | `dataset_manifest.json`, `schema.sql`, `workload.sql`, `plans.json` | DONE — real SQLite quick |
| Storage-budgeted index selection with no-index baseline, conditional greedy and exact ILP/oracle | 64 complete subsets; `subset_measurements.csv`, `strategy_comparison.csv` | DONE — interaction-aware quick |
| Latency, actual throughput, build/storage cost, plan changes and identical results | Raw timing/throughput CSVs; all subset checksums equal; focused tests | DONE — quick; full scale NOT RUN |

## I — Named quantum algorithms and QML

| Requirement | Executable evidence | Status |
|---|---|---|
| Deutsch–Jozsa, Bernstein–Vazirani, Grover, QFT, QPE and scoped Shor | `src/optlab/track_i.py`; analytic tests; `results/i/algorithms.csv` | DONE — local CPU simulator; Shor compiled for N=15 |
| Annealing plus QAOA/VQE coverage | Classical Metropolis annealing in I; executable QAOA/VQE in C | DONE — classical annealing simulation + quantum circuit simulation |
| At least two manually constructed circuits with known-output tests | Manual parity oracles, Grover, QFT/QPE and compiled modular permutations | DONE — simulator quick |
| Quantum kernel and variational classifier against classical models on identical splits | `qml_dataset.csv`, `qml_comparison.csv`, predictions and counts | DONE — held-out synthetic quick |
| Grover query/gate/wall-time comparison and noise evidence | Search timing, shot and synthetic depolarizing-noise CSVs | DONE — simulator quick; no hardware or advantage claim |
| Additional algorithms conditional on course-specific material | No supplied evidence establishes further named algorithms | PENDING CONFIRMATION |

## J — Software-engineering optimization

| Requirement | Executable evidence | Status |
|---|---|---|
| Authentic maintained source ≥1,000 LOC and measured real tests | 4,752 pre-J source LOC; 54 then-current tests × 3 profiles; source/cost CSVs | DONE — real pytest quick |
| Binary selection variables, weighted feature/fault objective and runtime budget | Maximum-coverage formulation; 25/50/75/100% budgets; focused tests | DONE — quick |
| Alphabetical baseline vs greedy maximum coverage and exact ILP with actual suite runs | `selection_comparison.csv`, selected tests and execution logs | DONE — quick |
| Safe fault set, observed detector matrix, overhead/trade-offs and unchanged normal CI | Six temporary-copy mutations; mutation logs/matrices; full CI retained | DONE — quick; full mutation/scaling NOT RUN |

## Repository and submission deliverables

| Deliverable | Evidence | Status |
|---|---|---|
| Reproducible Python environment and pinned dependency resolution | `pyproject.toml`, `uv.lock`, `docs/environment.md` | DONE |
| A–J code, focused tests, raw CSV/JSON results, plots and per-track explanations | `src/optlab`, `tests`, `results`, `tracks` | DONE for supplied explicit experiments |
| Fast integration suite and cross-track artifact validation | 56 passing tests; `src/optlab/validate_artifacts.py`; validation JSON/CSV | DONE |
| Original AI prompts, revisions, verification and commit references | `prompts/planning`, `prompts/a` … `prompts/j` | PARTIAL — tracked records exist; final response exports/screenshots and student review are missing |
| Three genuine AI-development failure records | `docs/failure_log.md` | PARTIAL — three corrections identified; C/H lack retained raw failure output |
| Independent same-task two-tool comparison | `docs/tool_comparison.md` | NOT RUN — requires an actual second tool run |
| Final technical report and polished live demonstration | `reports/technical_report.md`, `reports/demo.md` | PENDING — templates/evidence navigation only; final report intentionally not generated |
