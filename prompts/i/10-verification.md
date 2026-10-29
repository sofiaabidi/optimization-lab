# Prompt 10 — verification

Date: 2026-10-29

Commands actually run for the final implementation gate:

```text
MPLCONFIGDIR=/tmp/optlab-matplotlib OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 .venv/bin/pytest -q tests/test_track_i.py
7 passed in 3.10s

MPLCONFIGDIR=/tmp/optlab-matplotlib OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 .venv/bin/pytest -q -m 'not slow and not external'
49 passed in 8.16s

.venv/bin/python -m optlab list
exit 0; A-I reported DONE; J NOT IMPLEMENTED

.venv/bin/python -m optlab run --track i --profile full
exit 0; status NOT RUN

.venv/bin/python -m compileall -q src tests
exit 0

artifact consistency assertion
PASS: 7 named rows, 21 timing rows, Grover query/gate/shot/noise evidence, 20 annealing runs, identical 24/16 QML split, 4 models, all analytic checks, full NOT RUN
```

The successful quick profile completed in 22.862 s on PennyLane 0.45.1 `default.qubit`/`default.mixed`. Known outputs passed for constant/balanced Deutsch–Jozsa, Bernstein–Vazirani secret `101`, target-5 Grover, QFT round-trip of basis 5, phase-3/8 QPE, and compiled N=15 order finding/factors 3 and 5. At least six recorded rows use manual gate construction; Shor alone uses explicit compiled controlled modular-permutation matrices and is not presented as general scalable Shor.

Grover used 2 oracle calls, 43 high-level gates and depth 21, with target probability 0.9453125. Ascending classical search used 6 actual queries for target 5 (8 worst-case). Median statevector time was 7.271 ms versus 0.0062 ms classically, so no runtime advantage occurred. Six finite-shot runs and four density-matrix noise points were saved; target probability fell to 0.7359 at depolarizing probability 0.06.

On the identical seed-2026 24-train/16-test split, quantum-kernel accuracy was 0.8125 versus RBF kernel 0.875; the variational classifier achieved 0.875 versus trigonometric logistic regression 0.9375. Quantum costs were 660 overlap circuits/1.867 s and 6,736 executions/20.301 s, while classical training took 0.000174 s and 0.00728 s. These are simulator costs on a small synthetic dataset, not advantage evidence.

The first quick run failed only at artifact serialization after completing computation (`ValueError: dict contains fields not in fieldnames: 'uniform_magnitude_max_error'`). The ordered-union CSV fix has a focused regression test, and the successful rerun overwrote partial outputs. PennyLane's device-constructor shots deprecation warning remains a documented future API migration; results were unaffected.

Material limitations: no hardware; compiled N=15 Shor only; classical, not quantum, annealing; synthetic noise; analytic quantum-kernel overlaps; high-level rather than native/fault-tolerant gate counts; small synthetic held-out QML data; full profile `NOT RUN`; and additional syllabus-only algorithms remain unresolved because the authoritative Chapter 6 deck is absent. The final chat export and human review must be supplied by the student.
