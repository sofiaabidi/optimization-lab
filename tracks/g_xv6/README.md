# G — Real xv6-riscv priority scheduling

Status: **real QEMU quick profile executed** on 2026-10-29. Full profile is **NOT RUN**. This is a modification of the real MIT PDOS xv6-riscv kernel, not a Python scheduler model.

## Provenance and preserved baseline

- Official repository: `https://github.com/mit-pdos/xv6-riscv.git`
- Pinned commit: `e93dabeb98431235c6e1a101cb96c73c923fdbc4` (`tx_busy`, 2026-10-26)
- License: upstream MIT license, retained in the ignored checkout
- Toolchain: QEMU 10.2.1, RISC-V GCC 14.2.0, binutils 2.45.50.20251209, Make 4.4.1

The ignored `external/xv6-riscv-upstream` checkout remained at the exact upstream commit. A separate benchmark worktree added only the shared user harness and syscall-number reservations. Its compiled kernel SHA-256 was identical to pristine upstream: `4f5ddd710b706fd16625c25be1bf039bfd53fd7ed7d91848f6abdaeed19b0a5a`. The optimized kernel lived in another worktree.

Reviewable patches are tracked separately:

- [`0001-benchmark-harness.patch`](patches/0001-benchmark-harness.patch): identical user workload and ABI declarations for both variants.
- [`0002-priority-accounting.patch`](patches/0002-priority-accounting.patch): kernel scheduler and accounting changes only.
- [`xv6-track-g-complete.patch`](patches/xv6-track-g-complete.patch): complete literal diff from the pinned upstream commit.

## Kernel features

### Strict-priority scheduler

Every process has priority 0–3, where 0 is highest and 1 is the default. Children inherit their parent's priority. `setpriority(pid, priority)` validates the range and updates a live process under its process lock. Each CPU scans runnable processes for the highest priority and uses a per-CPU rotating start index to break equal-priority ties.

The objective is lower response time for explicitly important work. It is not a general throughput optimization. There is no aging, so a continuously runnable high-priority process can starve lower priorities. On multiple CPUs, lower-priority work may run while all higher-priority processes are already running on other CPUs.

### Scheduler accounting syscall

The distinct second kernel feature records scheduler dispatches and timer quanta per process. `getpstats(pid, struct pstat *)` returns PID, priority, dispatch count, and runtime ticks through a checked user-space copy. Counters are initialized for each process and timer accounting occurs immediately before a timer-driven yield. This is a diagnostic/observability feature, not a second performance optimization; the measured policy change is the priority scheduler.

## Real boot and stability gates

All tests below ran inside QEMU with the normal 128 MiB virtual machine and upstream virtio disk configuration. Boot/usertests used three harts.

| Kernel stage | Built | Boot marker | `usertests -q` terminal result |
|---|---:|---:|---|
| Untouched pinned upstream | yes | `xv6 kernel is booting`, harts 1 and 2 started | `ALL TESTS PASSED` |
| Priority scheduler + `setpriority` | yes | same three-hart boot | `ALL TESTS PASSED` |
| Accounting + `getpstats` | yes | same three-hart boot | `ALL TESTS PASSED` |

The `usertrap()` messages in memory-protection tests are expected test behavior; the corresponding tests report `OK`. Complete logs are [`baseline_boot_usertests.log`](../../results/g/baseline_boot_usertests.log), [`priority_usertests.log`](../../results/g/priority_usertests.log), and [`accounting_usertests.log`](../../results/g/accounting_usertests.log).

## Identical workload benchmark

Baseline and optimized benchmarks used the same `schedbench.c`, command order, 128 MiB RAM, virtio disk flags, three repeats, and `CPUS=1`. One CPU intentionally isolates scheduler policy; it is not a multicore scaling experiment. One xv6 uptime tick is approximately 0.1 seconds.

- **CPU response/turnaround:** one 30-million-iteration important job competes with five 60-million-iteration background jobs; all runs completed exactly 330 million iterations.
- **Mixed sleep/CPU:** the important job alternates six CPU bursts with one-tick sleeps while five background workers remain runnable.
- **Equal-priority contention/fairness:** six equal-priority workers run for 12 ticks. Fairness is the minimum/maximum completed-work ratio; 1 is best.

| Workload / metric (median of 3) | Upstream RR | Priority + accounting | Change |
|---|---:|---:|---:|
| CPU important-job response | 6 ticks | 1 tick | −83.3% |
| CPU makespan | 10 ticks | 11 ticks | +10.0% (worse) |
| CPU throughput | 33.0M work/tick | 30.0M | −9.1% |
| Mixed important-job response | 18 ticks | 6 ticks | −66.7% |
| Mixed makespan | 18 ticks | 15 ticks | −16.7% |
| Mixed work/tick | 9.309M | 8.648M | −7.1% |
| Equal-priority fairness ratio | 0.498 | 0.616 | +23.8% |
| Equal-priority total work/tick | 10.041M | 7.290M | −27.4% |

Priority substantially improved important-job latency, but CPU makespan and measured throughput did not improve. Equal-priority fairness happened to improve while total work fell; with three repeats and coarse ticks, this is an observed result, not a general guarantee. The optimized scheduler's full process-table scan adds overhead.

Raw console logs: [`baseline_benchmark.log`](../../results/g/baseline_benchmark.log) and [`optimized_benchmark.log`](../../results/g/optimized_benchmark.log). Parsed rows: [`benchmark.csv`](../../results/g/benchmark.csv), [`benchmark_summary.csv`](../../results/g/benchmark_summary.csv), and [`comparison.csv`](../../results/g/comparison.csv). Summary: [`summary.json`](../../results/g/summary.json).

## Reproduce

The preparation script refuses to overwrite an existing target:

```bash
tracks/g_xv6/prepare_xv6.sh baseline external/xv6-baseline-repro
tracks/g_xv6/prepare_xv6.sh optimized external/xv6-optimized-repro
```

Run and capture real QEMU tests non-interactively:

```bash
python tracks/g_xv6/run_qemu.py external/xv6-baseline-repro \
  'usertests -q' 'ALL TESTS PASSED' results/g/repro-baseline-usertests.log --cpus 3
python tracks/g_xv6/run_qemu.py external/xv6-optimized-repro \
  'usertests -q' 'ALL TESTS PASSED' results/g/repro-optimized-usertests.log --cpus 3
python tracks/g_xv6/run_qemu.py external/xv6-baseline-repro \
  'schedbench 3' 'SCHEDBENCH PASS' results/g/repro-baseline-benchmark.log --cpus 1
python tracks/g_xv6/run_qemu.py external/xv6-optimized-repro \
  'schedbench 3' 'SCHEDBENCH PASS' results/g/repro-optimized-benchmark.log --cpus 1
python -m optlab run --track g --profile quick
```

Patch application was separately checked in a fresh detached checkout, rebuilt, and the automated runner observed `SCHEDBENCH PASS` under QEMU.

## Limitations

Strict priority lacks aging and has a real starvation risk. Benchmarks use one emulated CPU, coarse 0.1-second ticks, small educational workloads, and only three repeats. Accounting records quanta rather than hardware cycles. QEMU results do not represent physical RISC-V hardware. Full benchmark sizes, multicore scaling, and starvation mitigation are not run.
