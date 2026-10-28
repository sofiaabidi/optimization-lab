# Prompt 06 — verification

Date: 2026-10-28

Commands actually run for the final implementation gate:

```text
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 .venv/bin/pytest -q tests/test_track_e.py
5 passed in 0.33s

OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 .venv/bin/python -m optlab run --track e --profile quick
exit 0; status DONE; total wall time 0.081709399 s

OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 MPLCONFIGDIR=/tmp/optlab-matplotlib .venv/bin/pytest -q -m 'not slow and not external'
29 passed in 3.40s

.venv/bin/python -m optlab list
exit 0; A-E reported DONE; F and H-J NOT IMPLEMENTED; G BLOCKED

.venv/bin/python -m compileall -q src tests
exit 0

artifact consistency assertion
PASS: 6 comparison, 12 scaling, 12 sensitivity rows; feasible rows have zero unmet/violations; infeasible LP has no cost; oracle error 0; full NOT RUN
```

On the fixed feasible case, first-available cost was `4.48`, cheapest-slot cost was `3.58`, and exact-LP cost was `3.40`; all delivered 20 kWh without constraint violations. Exact LP therefore saved `1.08` (24.1%) against baseline, while peak utilization remained 100% for both. Median measured runtimes were 0.121 ms, 0.118 ms, and 1.190 ms, respectively.

The deliberately infeasible vehicle request produced partial/infeasible statuses and was never labeled feasible. The exact solver returned `INFEASIBLE` with no schedule or cost. The independent tiny grid oracle and LP both produced objective `3.0` (absolute error zero).

Material limitations: inputs are synthetic and perfectly forecast; the LP omits discrete charger assignment, losses, battery tapering, uncertainty, and demand charges. The greedy heuristic was infeasible on some globally feasible sensitivity/scaling inputs. Timing is local and short; raw repeats are retained. Full profile is `NOT RUN`. The final chat response/export and human review must be captured by the student; neither is invented here.
