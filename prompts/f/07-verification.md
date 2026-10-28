# Prompt 07 — verification

Date: 2026-10-28

Commands actually run for the final implementation gate:

```text
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 .venv/bin/pytest -q tests/test_track_f.py
6 passed in 0.10s

OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 .venv/bin/python -m optlab run --track f --profile quick
exit 0; status DONE; total wall time 0.069107797 s

OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 MPLCONFIGDIR=/tmp/optlab-matplotlib .venv/bin/pytest -q -m 'not slow and not external'
35 passed in 10.40s

.venv/bin/python -m optlab list
exit 0; A-F reported DONE; G BLOCKED; H-J NOT IMPLEMENTED

.venv/bin/python -m compileall -q src tests
exit 0

artifact consistency assertion
PASS: 15 benchmarks, 210 raw timings, 4 changing/equivalent passes, 15 equivalent pipelines, DP training improvement, held-out non-generalization, 40 generated checks, full NOT RUN
```

All four named passes changed their targeted IR and preserved output. Across five fixtures and three strategies, AST, original IR, optimized IR, and bytecode outputs agreed in all 15 cases. Forty seeded generated programs passed the same checks during the experiment; focused tests checked 30 generated programs plus syntax, undefined-variable, precedence, CSE invalidation, and DP optimality behavior.

Exact subset DP explored 29 states and 42 transitions. On its separate training program, it retained 5 instructions while reducing code from 61 to 56 bytes versus the fixed order. On held-out totals, however, fixed order was better: 15 instructions / 162 bytes versus DP order's 17 / 191. Unoptimized totals were 27 / 317. This non-generalization is reported, not hidden.

Material limitations: the language and bytecode VM are educational, integer-only, and have no control flow, external input, functions, memory, division, or native-code backend. Only print output is observable. Microsecond timings are host-sensitive, and raw repeats are retained. Full profile is `NOT RUN`. The final chat response/export and human review must be captured by the student; neither is invented here.
