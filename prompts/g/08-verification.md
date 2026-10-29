# Prompt 08 — verification

Date: 2026-10-29

The required preflight passed before implementation: QEMU 10.2.1, RISC-V GCC 14.2.0, GNU ld 2.45.50.20251209 and GDB 17.1 were executable.

Real xv6/QEMU gates actually run:

```text
untouched pinned upstream, CPUS=3: boot marker observed; usertests -q -> ALL TESTS PASSED
priority scheduler + setpriority, CPUS=3: boot marker observed; usertests -q -> ALL TESTS PASSED
accounting + getpstats, CPUS=3: boot marker observed; usertests -q -> ALL TESTS PASSED

baseline shared harness, CPUS=1: schedbench 3 -> SCHEDBENCH PASS
optimized kernel, CPUS=1: schedbench 3 -> SCHEDBENCH PASS
fresh pinned checkout: both tracked patches applied cleanly; kernel/kernel and fs.img built successfully
automated runner smoke, fresh optimized checkout, CPUS=1: schedbench 1 -> SCHEDBENCH PASS
```

The full QEMU transcripts are preserved in `results/g/*usertests.log` and `results/g/*benchmark.log`. The baseline benchmark worktree's compiled kernel SHA-256 matched pristine upstream exactly: `4f5ddd710b706fd16625c25be1bf039bfd53fd7ed7d91848f6abdaeed19b0a5a`.

Final repository gates:

```text
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 .venv/bin/pytest -q tests/test_track_g.py
3 passed in 0.02s

OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 .venv/bin/python -m optlab run --track g --profile quick
exit 0; status DONE; captured real-QEMU artifacts validated

OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 MPLCONFIGDIR=/tmp/optlab-matplotlib .venv/bin/pytest -q -m 'not slow and not external'
38 passed in 11.63s

.venv/bin/python -m optlab list
exit 0; A-G reported DONE; H-J NOT IMPLEMENTED

.venv/bin/python -m compileall -q src tests
exit 0

artifact consistency assertion
PASS: 18 raw rows, 6 summaries, 12 comparisons, 3 usertests gates, nonempty patches, full NOT RUN
```

Measured medians show the intended latency trade-off, not universal improvement: CPU important-job response fell from 6 to 1 tick and mixed response from 18 to 6 ticks, while CPU makespan rose from 10 to 11 ticks and CPU throughput fell about 9.1%. Equal-priority fairness improved in these three repeats, but equal-priority work per tick fell. No quantum-like or hardware performance claim is made.

Material limitations: strict priorities have no aging and can starve low-priority work; benchmarks isolate policy on one emulated CPU, use coarse approximately 0.1-second ticks and only three repeats; accounting measures timer quanta rather than hardware cycles; QEMU is not physical RISC-V hardware; the full profile is `NOT RUN`.
