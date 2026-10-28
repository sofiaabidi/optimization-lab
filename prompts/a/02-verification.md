# Prompt 02 — verification

Date: 2026-10-28

Required precheck passed before implementation:

```text
qemu-system-riscv64 10.2.1
riscv64-unknown-elf-gcc 14.2.0
riscv64-unknown-elf-ld 2.45.50.20251209
gdb-multiarch 17.1
```

Commands actually run for the final gate:

```text
.venv/bin/pytest -q tests/test_track_a.py
4 passed in 1.73s

.venv/bin/python -m optlab run --track a --profile quick
exit 0; status DONE; 13 ridge runs; 3 repeats per stochastic method; wall time 1.709823795 s

.venv/bin/pytest -q -m 'not slow and not external'
12 passed in 1.90s

.venv/bin/python -m optlab list
exit 0; A reported DONE; remaining scaffold statuses preserved

artifact consistency assertion
exit 0; nine ridge method names across 13 rows, gradient/Gauss–Newton oracles and nonempty SVG verified
```

Measured artifacts are under `results/a/`. The analytic ridge objective is `0.3260684948522262`; manual/finite-difference gradient maximum absolute error is `1.0181377963e-10`; manual/PyTorch error is `4.4408920985e-16`; the HVP check error is `3.0839286680e-10`. Full profile status is `NOT RUN`.

Remaining evidence gap: the student must capture the actual final chat response/export and human review. No model ID, response transcript, or review is invented here. The implementation commit is recorded separately after Git creates it.
