# Prompt 04 — verification

Date: 2026-10-28

Commands actually run for the final implementation gate:

```text
MPLCONFIGDIR=/tmp/optlab-matplotlib .venv/bin/pytest -q tests/test_track_c.py
4 passed in 1.72s

MPLCONFIGDIR=/tmp/optlab-matplotlib .venv/bin/python -m optlab run --track c --profile quick
exit 0; status DONE; total wall time 6.347530885 s

MPLCONFIGDIR=/tmp/optlab-matplotlib .venv/bin/pytest -q -m 'not slow and not external'
20 passed in 4.07s

.venv/bin/python -m optlab list
exit 0; A, B, and C reported DONE; other scaffold statuses preserved

artifact consistency assertion
exit 0; 9 shot rows, 3 noise rows, 3 controlled optimizers, 72 plateau samples, QNN loss reduction, bounded evaluation counts, nonempty figure, and full NOT RUN verified
```

Correctness evidence: Track C's Max-Cut Hamiltonian was checked against Track B's cut value for every one of 16 basis states. Parameter-shift gradients agree with central finite differences. VQE energies respect the exact diagonalization bound. QAOA used the same classical optimum 6.5 and produced expectation cut `6.1423892593`, with optimal-state probability `0.4907647275`; it did not beat the oracle.

Measured simulator results: QAOA terminated normally after 160 energy evaluations; synthetic depolarizing probability 0.03 reduced expected cut to `5.721571`. At comparable budgets, parameter-shift, SPSA, and diagonal-metric QNG energy errors were `1.3111e-5`, `7.7104e-4`, and `1.3574e-5`. The QNN training loss fell from `0.084293` to `0.061316`. Width/depth gradient variance is stored without an asymptotic claim.

Genuine deviations/blockers: no hardware was available or attempted; noise is synthetic; QNG uses the documented diagonal metric approximation; full profile is `NOT RUN`. PennyLane emitted a finite-shot device-construction deprecation warning, but the run completed. The student must capture the final chat response/export and human review; no transcript or model ID is invented. The implementation commit is recorded after Git creates it.
