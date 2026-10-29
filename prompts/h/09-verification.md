# Prompt 09 — verification

Date: 2026-10-29

Commands actually run for the final implementation gate:

```text
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 .venv/bin/pytest -q tests/test_track_h.py
4 passed in 0.41s

OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 MPLCONFIGDIR=/tmp/optlab-matplotlib .venv/bin/pytest -q -m 'not slow and not external'
42 passed in 5.21s

.venv/bin/python -m optlab list
exit 0; A-H reported DONE; I-J NOT IMPLEMENTED

.venv/bin/python -m optlab run --track h --profile full
exit 0; status NOT RUN

.venv/bin/python -m compileall -q src tests
exit 0

artifact consistency assertion
PASS: 64 subsets, 4,800 latency rows, 6 actual throughput cycles, all checksums equal, budget feasible, 15 plan cases changed, full NOT RUN
```

The final quick profile used SQLite 3.53.1, seed 2026, 10,000 students, 60,000 enrollments, six candidates, all 64 subsets, five warm-cache latency repeats over three parameter cases, and three actual 100-query throughput cycles per unique selected configuration. Dataset generation took 0.208 s and was excluded from query latency.

The no-added-index baseline measured 275.892 ms weighted latency and 405.7 queries/s. Conditional greedy and exact measured-subset ILP independently selected the same three indexes (`idx_course_department`, `idx_enrollment_course_term`, `idx_student_advisor_status`), using 1,953,792 of 2,500,000 bytes. Both therefore report the same physical result: 30.603 ms weighted latency, 2,691.3 queries/s, and 43.64 ms index build time. The objective improved by 88.9%; exact ILP did not improve beyond greedy in this run.

Every query checksum matched the baseline across all 64 subsets. The chosen set changed all 15 query/case plans, replacing relevant table scans with measured covering/index searches. The exact ILP objective matched an independent exhaustive feasible-subset oracle. Complete-subset measurements and pair interactions were used; additivity was not assumed.

Material limitations: deterministic data are synthetic; timing is warm-cache, read-only, single-client WSL2 measurement; update/write amplification, cold cache, concurrent clients, production skew and full scale were not run. Exhaustive one-hot subset ILP is practical here only because six candidates yield 64 subsets. The final chat response/export and human review must be captured by the student; neither is invented here.
