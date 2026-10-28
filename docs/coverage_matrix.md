# Provisional Chapter 6 coverage matrix

This list preserves every requirement stated in `plan.md` §5. Additional syllabus-specific methods are still uncertain because no authoritative taught-method inventory has been supplied; that uncertainty is not an environment blocker. Every item is `NOT IMPLEMENTED`; text or a placeholder is not executable evidence.

| Track | Provisional requirement | Code / test / output evidence | Status |
|---|---|---|---|
| A | Loss + regularizer; parameters, objective, gradient, backward pass; continuous/discrete, convex/nonconvex, local/global minima, saddle examples | `src/optlab/track_a.py`; `tests/test_track_a.py`; `results/a/summary.json` | DONE (quick) |
| A | GD, SGD, mini-batch SGD, Momentum, NAG, AdaGrad, RMSProp, Adam, Newton, Gauss–Newton | `run_first_order`, `run_newton`, `gauss_newton_demo`; `results/a/raw.csv`, `histories.csv` | DONE (quick) |
| A | Backprop finite-difference/autograd check and Fisher/diagonal-Hessian/HVP curvature approximation | `backpropagation_check`, `curvature_check`; `test_newton_gauss_newton_and_backprop_oracles`; `results/a/summary.json` | DONE (quick) |
| A | Convex, strongly convex, nonconvex convergence; learning-rate, batch/noise and setting sensitivity | `landscape_examples`, `run_experiment`; `results/a/sensitivity.csv`, `trajectories.svg` | DONE (quick; full NOT RUN) |
| B | Knapsack/selection via greedy, ILP, branch-and-bound and DP; enumeration oracle | `greedy_knapsack`, `milp_knapsack`, `branch_and_bound_knapsack`, `dynamic_programming_knapsack`; `tests/test_track_b.py`; `results/b/knapsack_raw.csv` | DONE (quick) |
| B | Weighted Max-Cut enumeration, QUBO, Ising mapping and exhaustive energy equivalence | `tracks/b_discrete/maxcut_instance.json`; `maxcut_qubo`, `qubo_to_ising`, `enumerate_maxcut`; exhaustive test; `results/b/maxcut_energies.csv` | DONE (quick) |
| B | Constrained binary penalty-strength feasible/infeasible example | `cardinality_penalty_demo`; focused test; `results/b/penalty_sweep.csv` | DONE (quick) |
| B | Feature selection or other taught combinatorial example (syllabus decision open) | No authoritative syllabus evidence supplied | NOT IMPLEMENTED (syllabus decision open) |
| C | B Max-Cut QAOA circuit, finite shots and exhaustive comparison | `maxcut_hamiltonian`, `apply_qaoa`, `optimize_qaoa`; exhaustive basis test; `results/c/qaoa_optimization.csv`, `qaoa_shots.csv` | DONE (simulator quick) |
| C | Small-Hamiltonian VQE, PQC/QNN and hybrid training loop | `vqe_hamiltonian`, `optimize_vqe`, `train_qnn`; focused tests; `results/c/optimizer_comparison.csv`, `qnn_history.csv` | DONE (simulator quick) |
| C | Parameter-shift, SPSA and quantum natural gradient with documented metric | `parameter_shift_gradient`, `optimize_vqe`; finite-difference test; `results/c/optimizer_comparison.csv` | DONE (simulator quick) |
| C | Shot cost, simulator noise, barren-plateau illustration and embedding limitations | `qaoa_shot_experiment`, `qaoa_noise_experiment`, `barren_plateau_experiment`; `results/c/qaoa_noise.csv`, `barren_plateau_summary.csv`, `summary.json` | DONE (simulator quick; full NOT RUN) |
| D | Submodular coverage/facility objective, diminishing returns and greedy/exact comparison | `coverage_value`, `verify_diminishing_returns`, greedy/exhaustive oracles; `tests/test_track_d.py`; `results/d/summary.json` | DONE (quick) |
| D | Measured load balance, makespan, scheduling, work stealing, locality, synchronization and communication | `measure_scaling`, `measure_scheduling`, `measure_locality`, `measure_synchronization`, `measure_communication`; `results/d/*.csv` | DONE (local measured quick; shared-queue analogue disclosed) |
| D | Data, model and pipeline parallelism with actual/simulated distinction | `data_parallel_demo`, `model_parallel_demo`, `pipeline_parallel_demo`; PID/equivalence test; `results/d/parallel_patterns.csv` | DONE (local processes quick) |
| D | Measured Amdahl/Gustafson interpretation | `parallel_interpretation`; measured repeats in `parallel_scaling.csv`; `summary.json` | DONE (interpretation only) |
| D | FedAvg/centralized plus MGDA/GradNorm/equal-weight two-task comparisons | `centralized_training`, `fedavg_training`, `multitask_training`; focused tests; `results/d/fedavg.csv`, `multitask.csv` | DONE (sequential distributed simulation quick) |
| E | EV variables, cost objective, constraints and feasible/infeasible deterministic cases | `ChargingInstance`, `Vehicle`, `verify_schedule`; `tests/test_track_e.py`; `results/e/vehicles.csv`, `slots.csv` | DONE (synthetic quick) |
| E | First-available baseline, cheapest-feasible heuristic and exact LP/ILP | `first_available_schedule`, `cheapest_slot_schedule`, `exact_lp_schedule`; independent grid oracle; `results/e/comparison.csv` | DONE (continuous LP quick) |
| E | Strategy selection; cost, latency, peak, unmet energy, scaling and sensitivity | `tracks/e_ev_charging/README.md`; `results/e/benchmark_raw.csv`, `fleet_scaling.csv`, `capacity_sensitivity.csv` | DONE (quick; full NOT RUN) |
| F | Tiny compiler with behavioral-equivalence tests | — | NOT IMPLEMENTED |
| F | Constant folding/propagation, dead-code elimination and common-subexpression elimination | — | NOT IMPLEMENTED |
| F | Pass ordering/register allocation/scheduling optimization via greedy/DP/ILP | — | NOT IMPLEMENTED |
| F | Instruction count, runtime, code size, compile time and semantic equivalence | — | NOT IMPLEMENTED |
| G | Pinned upstream xv6 provenance, toolchain and reproducible patch setup | — | BLOCKED |
| G | First kernel feature plus distinct second full-credit feature | — | BLOCKED |
| G | Baseline/patched QEMU on CPU, yield/I-O and fairness workloads | — | BLOCKED |
| G | `usertests`, per-change smoke tests, logs and literal patch | — | BLOCKED |
| H | Seeded SQLite dataset, schema/workload, plans and repeatable measurement | — | NOT IMPLEMENTED |
| H | Storage-budget index-set optimization with baseline, greedy and exact DP/ILP | — | NOT IMPLEMENTED |
| H | Plans, latency, throughput, storage, build cost and result equality | — | NOT IMPLEMENTED |
| I | Taught algorithms; provisional DJ, BV, Grover, QFT, QPE, scoped Shor, annealing, QAOA/VQE | — | NOT IMPLEMENTED |
| I | At least two hand-built circuits with analytic checks | — | NOT IMPLEMENTED |
| I | Quantum kernel and variational classifier/QNN against fair classical baselines | — | NOT IMPLEMENTED |
| I | Grover theoretical/measured comparison; noise and limitations | — | NOT IMPLEMENTED |
| J | Authentic maintained source LOC ≥1,000 and real suite/fault profiling | — | NOT IMPLEMENTED |
| J | Test-choice variables, detection/coverage objective, time budget and constraints | — | NOT IMPLEMENTED |
| J | Alphabetical/full baseline versus taught greedy or DP/knapsack method | — | NOT IMPLEMENTED |
| J | Safe real/injected fault evidence, actual timing and maintainability | — | NOT IMPLEMENTED |
