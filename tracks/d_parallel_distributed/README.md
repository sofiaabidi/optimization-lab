# D — Submodular, parallel, distributed, and multi-task optimization

Status: **quick and full profiles executed**. The tables below preserve the original quick run; separate full artifacts are under [`results/d/full`](../../results/d/full/). The later technical audit added the measured deque work-stealing experiment to the primary quick evidence. Measurements used Python 3.11.18 with `OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=1` on the documented WSL2 host.

## Monotone submodular coverage

For six candidate facility sets and budget `k=3`, maximize the number of covered universe elements. Exhaustive checks evaluated 1,458 valid diminishing-return relations with zero violations. The objective is normalized, monotone, and submodular under a cardinality constraint, so the standard greedy `1-1/e` guarantee applies; no guarantee is claimed outside those conditions.

Greedy selected `(0,2,5)` and covered 10 elements. Exhaustive enumeration found the same selection/value, giving observed ratio `1.0`. This equality is instance-specific, not a stronger guarantee.

## Real CPU/process measurements

Worker pools were created and warmed before timing; task computation, scheduling, and IPC remained inside timed regions. Each scaling point has three repeats.

| Workers | Median wall time | Median speedup | Median efficiency | Observed range |
|---:|---:|---:|---:|---:|
| 1 | 0.6289 s | 1.000× | 100.0% | 0.5304–0.6689 s |
| 2 | 0.3039 s | 2.070× | 103.5% | 0.2954–0.3047 s |
| 4 | 0.2368 s | 2.656× | 66.4% | 0.1968–0.2391 s |

The 4-worker median implies an effective Amdahl parallel fraction `0.831` and a Gustafson scaled estimate `3.494`. The 2-worker superlinear result reflects measurement/cache/scheduling effects, not an algorithmic guarantee. These values interpret this measured workload only; they are not unmeasured scaling predictions.

### Scheduling, makespan, locality, synchronization, communication

- Coarse contiguous chunks took `0.2933 s`, with max/mean worker load `2.692`. Fine dynamic shared-queue scheduling took `0.1545 s`, with imbalance `1.088`, for the same checksum. This remains a shared-queue scheduling comparison, distinct from the deque experiment below.
- Contiguous gather median was `0.00129 s`; random gather median was `0.00641 s` for equal element counts, illustrating locality cost.
- Four threads incrementing under a shared lock took `0.02314 s`; thread-local counts plus reduction took `0.00395 s`, with identical result 100,000.
- Twelve 64-byte process messages took `0.00370 s`; twelve 1 MiB messages took `0.03186 s` (`376.7 MiB/s` effective payload throughput). Worker computation was constant-time, so this measures local serialization/IPC rather than network latency.

### Per-worker deque work stealing

The audit implementation gives each of four real worker processes its own fixed shared-memory deque and lock. An owner pops from the right; an idle worker scans other deques and steals from the left. Static and stealing runs start from the same intentionally skewed 16-task allocation, and process startup is excluded from the timed region.

| Policy | Wall time | Max/mean compute imbalance | Stolen tasks | Correctness |
|---|---:|---:|---:|---|
| Static per-worker deques | 0.3258 s | 2.145 | 0 | every task once; checksum match |
| Per-worker deques with stealing | 0.1477 s | 1.187 | 3 | every task once; checksum match |

This is a genuine deque-stealing demonstration, not a production lock-free runtime or a general speedup claim. Raw evidence is in [`work_stealing.csv`](../../results/d/work_stealing.csv), and the focused test verifies real steals, distinct worker PIDs, exact-once execution, checksums, and the owner/thief deque ends.

## Parallelism patterns

| Pattern | Serial | Parallel | Correctness | What actually overlapped |
|---|---:|---:|---:|---|
| Data parallel gradient | 0.000092 s | 0.002383 s | max error 2.66e-15 | two process PIDs computed row shards |
| Model parallel prediction | 0.000051 s | 0.002203 s | max error 1.78e-15 | two process PIDs computed feature-block partials |
| Two-stage pipeline | 0.2682 s | 0.1839 s | exact | two live process stages communicated through queues |

Data and model parallelism were slower because the educational tasks were far too small to amortize IPC. Pipeline startup was excluded, queue transfer included. Distinct worker PIDs and numerical equivalence are saved in `parallel_patterns.csv`.

## FedAvg versus centralized

All methods use the same seeded 240/80 train/test split and four non-IID client partitions. Client updates run sequentially in this educational simulation; communication is counted parameter payload, not measured networking.

| Method | Local steps | Rounds | Gradient evaluations | Payload bytes | Train loss | Test accuracy |
|---|---:|---:|---:|---:|---:|---:|
| Centralized | — | 50 | 50 | 0 | 0.26364 | 0.9625 |
| FedAvg | 1 | 10 | 40 | 1,920 | 0.43528 | 0.9375 |
| FedAvg | 1 | 30 | 120 | 5,760 | 0.30730 | 0.9625 |
| FedAvg | 5 | 10 | 200 | 1,920 | 0.27812 | 0.9625 |
| FedAvg | 5 | 30 | 600 | 5,760 | 0.20993 | 0.9625 |

More local computation reduced communication rounds for a given loss, but increased client gradient work. The lowest FedAvg training loss used 12 times the centralized gradient-evaluation count; held-out accuracy did not improve beyond 0.9625.

## Equal weighting, MGDA, and GradNorm

Two conflicting regression tasks share one two-parameter model. MGDA selects the minimum-norm convex gradient combination. GradNorm updates positive task weights from weighted gradient norms and relative training rates.

| Method | Task 1 loss | Task 2 loss | Mean loss | Final task weights |
|---|---:|---:|---:|---:|
| Equal | 1.47213 | 1.50358 | 1.48786 | 0.500 / 0.500 |
| MGDA | 1.33468 | 1.64779 | 1.49124 | 0.524 / 0.476 |
| GradNorm | 1.37595 | 1.60302 | 1.48949 | 0.521 / 0.479 |

MGDA and GradNorm favored Task 1 and worsened Task 2; neither improved mean loss over equal weighting on this run. That negative result is preserved rather than presented as superiority.

## Reproduce and artifacts

```bash
source .venv/bin/activate
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  python -m optlab run --track d --profile quick
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  pytest -q tests/test_track_d.py
```

Implementation: `src/optlab/track_d.py`. Summary: [`summary.json`](../../results/d/summary.json). Raw measurements: [`parallel_scaling.csv`](../../results/d/parallel_scaling.csv), [`scheduling.csv`](../../results/d/scheduling.csv), [`work_stealing.csv`](../../results/d/work_stealing.csv), [`locality.csv`](../../results/d/locality.csv), [`synchronization.csv`](../../results/d/synchronization.csv), [`communication.csv`](../../results/d/communication.csv), [`parallel_patterns.csv`](../../results/d/parallel_patterns.csv), [`fedavg.csv`](../../results/d/fedavg.csv), and [`multitask.csv`](../../results/d/multitask.csv).

## Limitations

Short local timings vary with OS scheduling and CPU state; raw repeats are retained. The shared ProcessPool queue remains only an analogue, while the separate locked shared-memory deque experiment performs actual steals but is still educational. BLAS behavior is controlled by environment variables but hardware counters were not collected. FedAvg is sequential simulation with analytical payload counts, not a real distributed network. The multi-task model is educational. Scaling beyond four workers was not run.
