# Prompt 03 — verification

Date: 2026-10-28

Commands actually run for the final implementation gate:

```text
.venv/bin/pytest -q tests/test_track_b.py
4 passed in 0.59s

.venv/bin/python -m optlab run --track b --profile quick
exit 0; status DONE; total wall time 0.046103201 s

.venv/bin/pytest -q -m 'not slow and not external'
16 passed in 1.93s

.venv/bin/python -m optlab list
exit 0; A and B reported DONE; other scaffold statuses preserved

artifact consistency assertion
exit 0; 5 knapsack method rows, all 16 Max-Cut states, 3 penalty strengths, stable instance path, and full NOT RUN verified
```

Measured results: knapsack oracle value 153; DP, branch-and-bound, and SciPy/HiGHS MILP exactly agree; ratio greedy value 152. Weighted Max-Cut optimum is 6.5. Across every bitstring, maximum `|QUBO + cut|` and `|QUBO - Ising|` are both 0. Penalties 0.5 and 2 select infeasible cardinalities; penalty 6 selects exactly one item.

Remaining scope: feature selection is `NOT IMPLEMENTED (syllabus decision open)` because no authoritative course evidence establishes whether it was taught. Full profile is `NOT RUN`. The student must capture the actual final chat response/export and human review; no transcript or model ID is invented. The implementation commit is recorded after Git creates it.
