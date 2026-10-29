# Provisional Chapter 6 coverage matrix

This list preserves every requirement stated in `plan.md` §5. Additional syllabus-specific methods are still uncertain because no authoritative taught-method inventory has been supplied; that uncertainty is not an environment blocker. Status is based on executable evidence; text or a placeholder alone is not evidence.

| Track | Provisional requirement | Code / test / output evidence | Status |
|---|---|---|---|
| A | Loss + regularizer; parameters, objective, gradient, backward pass; continuous/discrete, convex/nonconvex, local/global minima, saddle examples | `src/optlab/track_a.py`; `tests/test_track_a.py`; `results/a/summary.json` | DONE (quick) |
| A | GD, SGD, mini-batch SGD, Momentum, NAG, AdaGrad, RMSProp, Adam, Newton, Gauss–Newton | `run_first_order`, `run_newton`, `gauss_newton_demo`; `results/a/raw.csv`, `histories.csv` | DONE (quick) |
| A | Backprop finite-difference/autograd check and Fisher/diagonal-Hessian/HVP curvature approximation | `backpropagation_check`, `curvature_check`; `test_newton_gauss_newton_and_backprop_oracles`; `results/a/summary.json` | DONE (quick) |
| A | Convex, strongly convex, nonconvex convergence; learning-rate, batch/noise and setting sensitivity | `landscape_examples`, `run_experiment`; `results/a/sensitivity.csv`, `trajectories.svg` | DONE (quick + full) |
| B | Knapsack/selection via greedy, ILP, branch-and-bound and DP; enumeration oracle | `greedy_knapsack`, `milp_knapsack`, `branch_and_bound_knapsack`, `dynamic_programming_knapsack`; `tests/test_track_b.py`; `results/b/knapsack_raw.csv` | DONE (quick) |
| B | Weighted Max-Cut enumeration, QUBO, Ising mapping and exhaustive energy equivalence | `tracks/b_discrete/maxcut_instance.json`; `maxcut_qubo`, `qubo_to_ising`, `enumerate_maxcut`; exhaustive test; `results/b/maxcut_energies.csv` | DONE (quick) |
| B | Constrained binary penalty-strength feasible/infeasible example | `cardinality_penalty_demo`; focused test; `results/b/penalty_sweep.csv` | DONE (quick) |
| B | Feature selection or other taught combinatorial example (syllabus decision open) | No authoritative syllabus evidence supplied | NOT IMPLEMENTED (syllabus decision open) |
| C | B Max-Cut QAOA circuit, finite shots and exhaustive comparison | `maxcut_hamiltonian`, `apply_qaoa`, `optimize_qaoa`; exhaustive basis test; `results/c/qaoa_optimization.csv`, `qaoa_shots.csv` | DONE (simulator quick) |
| C | Small-Hamiltonian VQE, PQC/QNN and hybrid training loop | `vqe_hamiltonian`, `optimize_vqe`, `train_qnn`; focused tests; `results/c/optimizer_comparison.csv`, `qnn_history.csv` | DONE (simulator quick) |
| C | Parameter-shift, SPSA and quantum natural gradient with documented metric | `parameter_shift_gradient`, `optimize_vqe`; finite-difference test; `results/c/optimizer_comparison.csv` | DONE (simulator quick) |
| C | Shot cost, simulator noise, barren-plateau illustration and embedding limitations | `qaoa_shot_experiment`, `qaoa_noise_experiment`, `barren_plateau_experiment`; `results/c/qaoa_noise.csv`, `barren_plateau_summary.csv`, `summary.json` | DONE (simulator quick + full) |
| D | Submodular coverage/facility objective, diminishing returns and greedy/exact comparison | `coverage_value`, `verify_diminishing_returns`, greedy/exhaustive oracles; `tests/test_track_d.py`; `results/d/summary.json` | DONE (quick) |
| D | Measured load balance, makespan, scheduling, work stealing, locality, synchronization and communication | `measure_scaling`, `measure_scheduling`, `measure_locality`, `measure_synchronization`, `measure_communication`; `results/d/*.csv` | DONE (local measured quick; shared-queue analogue disclosed) |
| D | Data, model and pipeline parallelism with actual/simulated distinction | `data_parallel_demo`, `model_parallel_demo`, `pipeline_parallel_demo`; PID/equivalence test; `results/d/parallel_patterns.csv` | DONE (local processes quick) |
| D | Measured Amdahl/Gustafson interpretation | `parallel_interpretation`; measured repeats in `parallel_scaling.csv`; `summary.json` | DONE (interpretation only) |
| D | FedAvg/centralized plus MGDA/GradNorm/equal-weight two-task comparisons | `centralized_training`, `fedavg_training`, `multitask_training`; focused tests; `results/d/fedavg.csv`, `multitask.csv` | DONE (sequential distributed simulation quick) |
| E | EV variables, cost objective, constraints and feasible/infeasible deterministic cases | `ChargingInstance`, `Vehicle`, `verify_schedule`; `tests/test_track_e.py`; `results/e/vehicles.csv`, `slots.csv` | DONE (synthetic quick) |
| E | First-available baseline, cheapest-feasible heuristic and exact LP/ILP | `first_available_schedule`, `cheapest_slot_schedule`, `exact_lp_schedule`; independent grid oracle; `results/e/comparison.csv` | DONE (continuous LP quick) |
| E | Strategy selection; cost, latency, peak, unmet energy, scaling and sensitivity | `tracks/e_ev_charging/README.md`; `results/e/benchmark_raw.csv`, `fleet_scaling.csv`, `capacity_sensitivity.csv` | DONE (quick + full) |
| F | Tiny compiler with behavioral-equivalence tests | Lexer/parser/AST/lowering/bytecode VM in `track_f.py`; `tests/test_track_f.py`; `results/f/equivalence.csv` | DONE (quick) |
| F | Constant folding/propagation, dead-code elimination and common-subexpression elimination | Four pass functions; targeted change/equivalence tests; `results/f/pass_effects.csv`, `ir_snapshots.json` | DONE (quick) |
| F | Pass ordering/register allocation/scheduling optimization via greedy/DP/ILP | `optimize_pass_order_dp`; separate training program; `results/f/pass_order_search.csv` | DONE (exact subset DP quick) |
| F | Instruction count, runtime, code size, compile time and semantic equivalence | `results/f/benchmark.csv`, `benchmark_raw.csv`, `summary.json`; focused generated-program tests | DONE (Python VM quick + full) |
| G | Pinned upstream xv6 provenance, toolchain and reproducible patch setup | SHA `e93dab...`; `prepare_xv6.sh`; `patches/*.patch`; Track G README | DONE (real xv6) |
| G | First kernel feature plus distinct second full-credit feature | Strict-priority scheduler/`setpriority`; dispatch/tick accounting/`getpstats`; literal kernel patch | DONE (real kernel quick) |
| G | Baseline/patched QEMU on CPU, yield/I-O and fairness workloads | `schedbench.c` in harness patch; `results/g/*benchmark.log`, `benchmark.csv`, `comparison.csv` | DONE (QEMU, 3 repeats) |
| G | `usertests`, per-change smoke tests, logs and literal patch | Three boot/usertest logs end `ALL TESTS PASSED`; complete upstream-relative patch | DONE (baseline + each kernel change) |
| H | Seeded SQLite dataset, schema/workload, plans and repeatable measurement | `track_h.py`; `dataset_manifest.json`; `schema.sql`; `workload.sql`; 64 real subsets | DONE (SQLite quick) |
| H | Storage-budget index-set optimization with baseline, greedy and exact DP/ILP | Conditional measured greedy; exact one-hot subset ILP; exhaustive oracle; `subset_measurements.csv` | DONE (interaction-aware quick) |
| H | Plans, latency, throughput, storage, build cost and result equality | `plans.json`; `latency_raw.csv`; `throughput_raw.csv`; `strategy_comparison.csv`; focused tests | DONE (all 64 checksum-equal; full NOT RUN) |
| I | Taught algorithms; provisional DJ, BV, Grover, QFT, QPE, scoped Shor, annealing, QAOA/VQE | `track_i.py`; `algorithms.csv`; classical annealing; Track C cross-links | DONE (listed quick; syllabus reconciliation open) |
| I | At least two hand-built circuits with analytic checks | Manual parity oracles, Grover and QFT/QPE; focused known-output tests | DONE (simulator quick) |
| I | Quantum kernel and variational classifier/QNN against fair classical baselines | Same `qml_dataset.csv` splits; `qml_comparison.csv`; predictions and circuit counts | DONE (held-out synthetic quick) |
| I | Grover theoretical/measured comparison; noise and limitations | `grover_search_timing.csv`, `grover_shots.csv`, `grover_noise.csv`; query/gate counts | DONE (simulator/noise quick; no advantage) |
| J | Authentic maintained source LOC ≥1,000 and real suite/fault profiling | 4,752 pre-J maintained source lines; 54 tests × 3 profiles; `source_loc.csv`, `test_costs.csv` | DONE (real pytest quick) |
| J | Test-choice variables, detection/coverage objective, time budget and constraints | Binary `x_t/y_k` maximum-coverage ILP; 25/50/75/100% budgets; focused formulation tests | DONE (quick) |
| J | Alphabetical/full baseline versus taught greedy or DP/knapsack method | Alphabetical prefix vs greedy weighted maximum coverage vs exact ILP; actual selected-suite executions | DONE (quick) |
| J | Safe real/injected fault evidence, actual timing and maintainability | Six labeled temporary-copy mutations; observed detector matrix/logs; normal CI unchanged | DONE (synthetic mutations disclosed; full NOT RUN) |
