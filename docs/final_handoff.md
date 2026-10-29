# Final implementation handoff

This is an implementation and evidence handoff, not the final technical report. It records what was actually run on 2026-10-29. Primary `results/<track>/` artifacts are bounded quick profiles; A–F full profiles are preserved separately in `results/<track>/full/`. G–J full profiles remain explicitly `NOT RUN` rather than being inferred from quick results.

## Verification snapshot

- Full fast suite: **PASS**, 56 tests in 4.81 s with slow/external tests excluded after the Track D audit.
- Cross-track artifact validation: **PASS**, A–J with 53 declared invariants; machine-readable output is `results/artifact_validation.json` and `.csv`.
- Full profiles: **PASS/DONE** for A–F. D completed and wrote all artifacts, but the outer shell did not retain a trustworthy total duration, so none is claimed.
- Deferred profiles: G full external scaling, H full SQLite scale, I full quantum breadth/QML, and J full mutation/scaling are **NOT RUN**. Their CLIs were invoked and returned that status.
- Registry/CLI smoke: **PASS**; all ten tracks report `DONE` for their implemented milestones.

Track J's experiment profiled the then-current 54-test suite. The 55th test was the subsequently added A–J artifact-consistency test, and the 56th is the later deque work-stealing correctness test. These historical differences are preserved rather than retroactively changing the measured J run.

## Track status and findings

| Track | Implementation and verification | Measured finding | Remaining limitation |
|---|---|---|---|
| A | Continuous optimizers, curvature/backprop checks, stochastic repeats; quick and full DONE | Full analytic optimum objective `0.326068495`; manual/autograd and finite-difference gradients agree | Synthetic regression only; timing is host-specific |
| B | Knapsack greedy/DP/B&B/MILP plus exhaustive oracle; Max-Cut QUBO/Ising equivalence; quick and full DONE | Full knapsack oracle value `194`; all exact methods agree; Max-Cut optimum `6.5` | Extra syllabus-only feature-selection item remains open |
| C | Track-B QAOA, VQE optimizers, QNN, shots/noise/gradient variance; simulator quick and full DONE | Full QAOA expectation `6.142389 < 6.5` oracle; QNN accuracy `1.0` on its small task | Simulator/synthetic noise only; no quantum advantage or hardware claim |
| D | Submodular oracle, real local process patterns, scaling, communication, deque work stealing, FedAvg and multi-task methods; quick and full DONE | Full greedy coverage equals exact (`10`); in the later quick audit, deque stealing moved 3 tasks and reduced imbalance from `2.145` to `1.187` with exact-once/checksum correctness | Locked educational deques, not a production runtime; FedAvg is sequential distributed simulation; one local host |
| E | Feasible campus model, baseline, cheapest-slot heuristic, exact LP, oracle and sensitivity; quick and full DONE | Full LP cost `3.40` vs baseline `4.48`; peak stayed at 100%, so cost improved but peak did not | Deterministic synthetic demand; continuous charging model |
| F | Parser/IR/VM and four passes; exact subset-DP pass ordering; generated equivalence checks; quick and full DONE | Full fixed order: 15 instructions vs 27 unoptimized; DP order used 17 and did not generalize best; 400 generated programs remained equivalent | Educational language and Python VM timings |
| G | Pinned xv6 baseline, priority scheduler, accounting syscall, literal patch; real QEMU boot/usertests and three-workload benchmark PASS | Important-job response improved 83.3% (CPU) and 66.7% (mixed), but CPU makespan and throughput worsened | No physical hardware, multicore scaling, aging, or full profile |
| H | Seeded SQLite data/workload, 64 measured subsets, conditional greedy and exact measured-subset ILP; query equality PASS | All subset results match; greedy and exact selected the same budget-feasible physical indexes | One SQLite/WSL2 host; full scale profile not run |
| I | Manual DJ/BV/Grover/QFT/QPE and compiled N=15 Shor circuits; annealing and matched QML baselines; correctness PASS | Grover used 2 oracle calls but was slower than 6-query Python search; both classical QML baselines matched or exceeded quantum accuracy | No hardware/general Shor/quantum advantage; syllabus reconciliation and full profile open |
| J | 4,752 pre-J maintained source LOC, 54 real tests × 3 timing repeats, six isolated mutations, greedy and exact maximum coverage | Greedy matched exact at all budgets and detected 6/6 mutations at 25%; alphabetical detected 0/6 there; all selected suites passed | Synthetic fault sample, metadata coverage, single host; full mutation breadth not run |

The detailed limitations and raw-artifact links remain in each `tracks/<track>/README.md`; this handoff does not replace them.

## Exact reproduction commands

Start from the repository root with the locked Python 3.11 environment:

```bash
uv sync --all-extras --locked
source .venv/bin/activate
export MPLCONFIGDIR=/tmp/optlab-matplotlib
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
```

Run any bounded quick profile, or all ten sequentially:

```bash
python -m optlab run --track j --profile quick
python -m optlab run --all --profile quick
```

Recreate the completed A–F full profiles without overwriting quick artifacts:

```bash
python -c "from pathlib import Path; from optlab.track_a import run_experiment; print(run_experiment('full', Path('results/a/full')))"
python -c "from pathlib import Path; from optlab.track_b import run_experiment; print(run_experiment('full', Path('results/b/full')))"
python -c "from pathlib import Path; from optlab.track_c import run_experiment; print(run_experiment('full', Path('results/c/full')))"
python -c "from pathlib import Path; from optlab.track_d import run_experiment; print(run_experiment('full', Path('results/d/full')))"
python -c "from pathlib import Path; from optlab.track_e import run_experiment; print(run_experiment('full', Path('results/e/full')))"
python -c "from pathlib import Path; from optlab.track_f import run_experiment; print(run_experiment('full', Path('results/f/full')))"
```

Recreate Track G from fresh pinned baseline and optimized trees, then run the real gates:

```bash
tracks/g_xv6/prepare_xv6.sh baseline external/xv6-baseline-repro
tracks/g_xv6/prepare_xv6.sh optimized external/xv6-optimized-repro
python tracks/g_xv6/run_qemu.py external/xv6-baseline-repro 'usertests -q' 'ALL TESTS PASSED' results/g/repro-baseline-usertests.log --cpus 3
python tracks/g_xv6/run_qemu.py external/xv6-optimized-repro 'usertests -q' 'ALL TESTS PASSED' results/g/repro-optimized-usertests.log --cpus 3
python tracks/g_xv6/run_qemu.py external/xv6-baseline-repro 'schedbench 3' 'SCHEDBENCH PASS' results/g/repro-baseline-benchmark.log --cpus 1
python tracks/g_xv6/run_qemu.py external/xv6-optimized-repro 'schedbench 3' 'SCHEDBENCH PASS' results/g/repro-optimized-benchmark.log --cpus 1
python -m optlab run --track g --profile quick
```

Run the final gates:

```bash
pytest -q -m 'not slow and not external'
python -m optlab.validate_artifacts --output-dir results
python -m optlab list
```

## Evidence and unresolved assignment gaps

- Per-track original prompts, revision notes, verification records and commit records live under `prompts/a` through `prompts/j`. The tracked revisions preserve genuine corrections; no missing transcript or screenshot has been invented.
- The exact Codex model identifier is unavailable and remains `unknown`. Final chat exports/screenshots and student human-review notes still require manual capture.
- `docs/failure_log.md` is not yet a complete three-case submission record: genuine development corrections exist in the C, H and I revision notes, but only I retained an exact failure message. Missing raw failure output must not be reconstructed.
- The supplied assignment baseline is fully mapped. The conditional B feature-selection item and any additional course-specific I algorithms remain pending confirmation in `docs/coverage_matrix.md`.
- The requested final technical report was intentionally not produced. Physical quantum/RISC-V hardware, quantum advantage, xv6 full scaling, and G–J full profiles remain unverified.
- GitHub Actions must rerun after these commits are pushed. No push is performed by this handoff.
