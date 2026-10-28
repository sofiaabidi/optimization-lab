# Prompt 05 — verification

Date: 2026-10-28

Commands actually run for the final implementation gate:

```text
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 .venv/bin/pytest -q tests/test_track_d.py
4 passed in 0.18s

OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 .venv/bin/python -m optlab run --track d --profile quick
exit 0; status DONE; total wall time 4.622825129 s

OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 MPLCONFIGDIR=/tmp/optlab-matplotlib .venv/bin/pytest -q -m 'not slow and not external'
24 passed in 3.73s

.venv/bin/python -m optlab list
exit 0; A-D reported DONE; remaining scaffold statuses preserved

artifact consistency assertion
exit 0; 9 scaling rows, matching scheduling checksums, 3 real-process patterns with numerical equality, 5 centralized/FedAvg rows, 3 valid multi-task rows, and full NOT RUN verified
```

Measured results: exhaustive submodularity checks passed 1,458/1,458 and greedy matched exact coverage 10. Median four-worker speedup was `2.6558` with efficiency `0.6639`; the Amdahl-inferred fraction was `0.8313` and the descriptive Gustafson estimate `3.4939`. Fine dynamic scheduling reduced wall time from `0.2933 s` to `0.1545 s` and load imbalance from `2.692` to `1.088` for the same checksum.

FedAvg used the same split and four client partitions as centralized training. Its four configurations varied local steps 1/5 and rounds 10/30, recording gradient evaluations and 1,920/5,760 payload bytes. Equal weighting had the best mean two-task loss (`1.48786`); MGDA and GradNorm changed the task trade-off but did not improve that mean.

Material deviations/limitations: ProcessPool's shared dynamic queue is measured only as a work-stealing analogue, not a deque-based work-stealing implementation. Data/model parallel examples were slower because IPC dominated. FedAvg clients were simulated sequentially and communication bytes are payload counts, not network measurements. Full profile is `NOT RUN`. The student must capture the final chat response/export and human review; no transcript or model ID is invented. The implementation commit is recorded after Git creates it.
