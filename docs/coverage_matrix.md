# Provisional Chapter 6 coverage matrix

This list preserves every requirement stated in `plan.md` §5. Additional syllabus-specific methods are still uncertain because no authoritative taught-method inventory has been supplied; that uncertainty is not an environment blocker. Every item is `NOT IMPLEMENTED`; text or a placeholder is not executable evidence.

| Track | Provisional requirement | Code / test / output evidence | Status |
|---|---|---|---|
| A | Loss + regularizer; parameters, objective, gradient, backward pass; continuous/discrete, convex/nonconvex, local/global minima, saddle examples | `src/optlab/track_a.py`; `tests/test_track_a.py`; `results/a/summary.json` | DONE (quick) |
| A | GD, SGD, mini-batch SGD, Momentum, NAG, AdaGrad, RMSProp, Adam, Newton, Gauss–Newton | `run_first_order`, `run_newton`, `gauss_newton_demo`; `results/a/raw.csv`, `histories.csv` | DONE (quick) |
| A | Backprop finite-difference/autograd check and Fisher/diagonal-Hessian/HVP curvature approximation | `backpropagation_check`, `curvature_check`; `test_newton_gauss_newton_and_backprop_oracles`; `results/a/summary.json` | DONE (quick) |
| A | Convex, strongly convex, nonconvex convergence; learning-rate, batch/noise and setting sensitivity | `landscape_examples`, `run_experiment`; `results/a/sensitivity.csv`, `trajectories.svg` | DONE (quick; full NOT RUN) |
| B | Knapsack/selection via greedy, ILP, branch-and-bound and DP; enumeration oracle | — | NOT IMPLEMENTED |
| B | Weighted Max-Cut enumeration, QUBO, Ising mapping and exhaustive energy equivalence | — | NOT IMPLEMENTED |
| B | Constrained binary penalty-strength feasible/infeasible example | — | NOT IMPLEMENTED |
| B | Feature selection or other taught combinatorial example (syllabus decision open) | — | NOT IMPLEMENTED |
| C | B Max-Cut QAOA circuit, finite shots and exhaustive comparison | — | NOT IMPLEMENTED |
| C | Small-Hamiltonian VQE, PQC/QNN and hybrid training loop | — | NOT IMPLEMENTED |
| C | Parameter-shift, SPSA and quantum natural gradient with documented metric | — | NOT IMPLEMENTED |
| C | Shot cost, simulator noise, barren-plateau illustration and embedding limitations | — | NOT IMPLEMENTED |
| D | Submodular coverage/facility objective, diminishing returns and greedy/exact comparison | — | NOT IMPLEMENTED |
| D | Measured load balance, makespan, scheduling, work stealing, locality, synchronization and communication | — | NOT IMPLEMENTED |
| D | Data, model and pipeline parallelism with actual/simulated distinction | — | NOT IMPLEMENTED |
| D | Measured Amdahl/Gustafson interpretation | — | NOT IMPLEMENTED |
| D | FedAvg/centralized plus MGDA/GradNorm/equal-weight two-task comparisons | — | NOT IMPLEMENTED |
| E | EV variables, cost objective, constraints and feasible/infeasible deterministic cases | — | NOT IMPLEMENTED |
| E | First-available baseline, cheapest-feasible heuristic and exact LP/ILP | — | NOT IMPLEMENTED |
| E | Strategy selection; cost, latency, peak, unmet energy, scaling and sensitivity | — | NOT IMPLEMENTED |
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
