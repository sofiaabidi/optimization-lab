# J — CI test selection and prioritization

Status: **real pytest quick profile executed** on 2026-10-29. The full mutation/scaling profile is **NOT RUN**. The normal GitHub Actions workflow still runs the complete fast suite; this experiment does not weaken, skip, or rewrite CI tests.

## Authentic codebase and measured costs

Before Track J additions, this repository contained 4,752 nonblank, non-comment physical Python lines across 18 maintained files in `src/optlab`. Tests, generated files, dependencies, `track_j.py`, and the profiling helper are excluded. This comfortably clears the required 1,000-source-LOC gate without padding or an external codebase.

The experiment uses a pytest hook to record precise setup, call, and teardown durations for all 54 then-current fast tests over three complete suite runs. Median full subprocess wall time was 7.029 s; summed median test phases were 3.060 s. The difference is fixed collection, imports, interpreter startup, and plugin/simulator initialization. Optimization budgets constrain measured test phases, while actual selected-suite wall time is separately executed and reported.

## Optimization formulation

For test `t`, binary `x_t` selects it. Each behavior/feature or observed injected-fault detector `k` has binary coverage variable `y_k` and weight `w_k`; injected faults receive weight 5 and ordinary features weight 1.

```text
maximize   sum_k w_k y_k
subject to sum_t measured_cost_t x_t <= budget
           y_k <= sum_{t covers k} x_t
           x_t, y_k in {0,1}
```

Features are grounded in real test component/node names and assertions, plus explicit cross-track tags such as oracle, equivalence, reproducibility, noise, and shared Max-Cut representation. This is not line-coverage instrumentation.

Compared strategies:

- **Alphabetical prefix:** naïve pytest node order until the next test would exceed the phase budget.
- **Greedy weighted maximum coverage:** repeatedly selects the feasible largest marginal weighted coverage per measured second.
- **Exact maximum-coverage ILP:** SciPy/HiGHS solves the binary model, then the selected set is prioritized by the same marginal-coverage rule.

## Safe injected-fault evidence

Six deliberately injected mutations target real A, B, E, F, H, and I behavior: ridge-gradient sign, Max-Cut edge predicate, EV capacity sign, compiler addition semantics, index-budget comparator, and compiled-Shor modular multiplication. Each mutation is applied only inside a temporary copied `src/optlab`; the associated real track test file is executed in a fresh subprocess, then the temporary tree is discarded. These are synthetic mutation-testing faults, **not observed production defects**.

All six mutations were detected. The conservative matrix credits only failing test node IDs observed in that mutation's scoped run; it does not assume that unexecuted cross-track tests would detect anything.

## Measured selection results

| Phase budget | Method | Tests | Weighted objective | Detected faults | Predicted phases | Actual wall | Selection overhead |
|---:|---|---:|---:|---:|---:|---:|---:|
| 25% | Alphabetical | 10 | 14 | 0/6 | 0.044 s | 0.969 s | 0.007 ms |
| 25% | Greedy | 51 | 98 | 6/6 | 0.697 s | 3.793 s | 1.183 ms |
| 25% | Exact ILP | 51 | 98 | 6/6 | 0.697 s | 3.839 s | 8.976 ms |
| 50% | Alphabetical | 10 | 14 | 0/6 | 0.044 s | 0.902 s | 0.011 ms |
| 50% | Greedy | 53 | 100 | 6/6 | 1.296 s | 4.304 s | 1.022 ms |
| 50% | Exact ILP | 53 | 100 | 6/6 | 1.296 s | 4.461 s | 4.979 ms |
| 75% | Alphabetical | 40 | 80 | 5/6 | 2.261 s | 5.821 s | 0.008 ms |
| 75% | Greedy | 53 | 100 | 6/6 | 1.296 s | 4.459 s | 1.184 ms |
| 75% | Exact ILP | 53 | 100 | 6/6 | 1.296 s | 4.019 s | 4.322 ms |
| 100% | All strategies | 54 | 101 | 6/6 | 3.060 s | 6.54–7.11 s | 0.009–3.236 ms |

Greedy matched the exact ILP at every bounded budget, so exact optimization produced no coverage improvement here. The alphabetical prefix underused 25% and 50% budgets because the next slow test blocked the prefix; this is a property of the declared naïve ordering baseline, not a claim about pytest's default full-suite policy. All 12 actually selected suites returned exit code zero. At 100%, every method becomes the complete suite.

## Reproduce and artifacts

```bash
MPLCONFIGDIR=/tmp/optlab-matplotlib \
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  python -m optlab run --track j --profile quick
pytest -q tests/test_track_j.py
pytest -q -m 'not slow and not external'
```

- Source threshold and test costs: [`source_loc.csv`](../../results/j/source_loc.csv), [`test_costs.csv`](../../results/j/test_costs.csv), [`test_profile_raw.csv`](../../results/j/test_profile_raw.csv)
- Grounded matrices: [`feature_matrix.csv`](../../results/j/feature_matrix.csv), [`fault_detection_matrix.csv`](../../results/j/fault_detection_matrix.csv)
- Mutation outcomes/logs: [`mutations.csv`](../../results/j/mutations.csv), [`mutation_logs/`](../../results/j/mutation_logs/)
- Selection and execution: [`selection_comparison.csv`](../../results/j/selection_comparison.csv), [`selected_tests.csv`](../../results/j/selected_tests.csv), [`execution_logs/`](../../results/j/execution_logs/)
- Early detection and summary: [`early_detection.csv`](../../results/j/early_detection.csv), [`summary.json`](../../results/j/summary.json)

## Limitations

Mutation faults are synthetic and only six operators/tracks are sampled. Feature coverage is semantic metadata, not measured line/branch coverage. Timing has three repeats on one WSL2 host, and import/collection startup dominates small selections. Fault credit is scoped conservatively, while early-detection time is reconstructed from real per-test medians rather than rerunning every selected ordering against every mutation. Test-selection optimization can lose unmodeled correctness, so normal CI intentionally remains the full suite. Full mutation breadth, multiple machines, historical real failures, flaky-test modeling, and maintenance-cost studies are not run.
