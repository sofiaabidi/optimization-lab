# Optimization Lab

Optimization Lab is the reproducible repository for Assignment 8, a ten-track study spanning continuous and discrete optimization, quantum simulation, parallel and distributed methods, an EV-charging case study, compiler optimization, a real xv6-riscv kernel modification, SQLite index selection, quantum algorithms/QML, and CI test selection.

Every track has executable code, focused correctness tests, machine-readable results, measured comparisons, and documented limitations. Bounded quick profiles exist for A–J; separate full-profile artifacts were executed for A–F. G–J full profiles remain `NOT RUN` because their verified quick evidence covers the required bounded experiments or the full workflow is intentionally external.

## Tracks and measured outcomes

| Track | Scope | Key measured outcome | Execution |
|---|---|---|---|
| [A](tracks/a_continuous/README.md) | Continuous optimization and foundations | Ridge optimum `0.326068495`; manual gradient agrees with autograd to `4.44e-16` | Quick + full |
| [B](tracks/b_discrete/README.md) | Knapsack, Max-Cut, QUBO and Ising | Quick exact knapsack value `153` vs greedy `152`; Max-Cut optimum `6.5` with exact energy equivalence | Quick + full |
| [C](tracks/c_quantum_opt/README.md) | QAOA, VQE and hybrid quantum optimization | Simulated QAOA expectation `6.142389` vs classical optimum `6.5`; shot/noise effects retained | Simulator quick + full |
| [D](tracks/d_parallel_distributed/README.md) | Submodular, parallel, federated and multi-task methods | Deque stealing moved 3 tasks and reduced measured imbalance from `2.145` to `1.187`; all checksums matched | Quick + full; deque audit in quick |
| [E](tracks/e_ev_charging/README.md) | Campus EV charging | Exact LP cost `3.40` vs baseline `4.48`; peak remained 100%, so it did not improve | Quick + full |
| [F](tracks/f_compiler/README.md) | Mini-compiler and pass ordering | Fixed passes reduced 27 instructions to 15; DP-selected order used 17 and did not generalize best | Quick + full |
| [G](tracks/g_xv6/README.md) | Real xv6-riscv priority scheduling | Important-job response improved from 6 to 1 CPU ticks; CPU makespan/throughput worsened | Real QEMU quick; full `NOT RUN` |
| [H](tracks/h_dbms/README.md) | SQLite index selection | Greedy matched exact ILP; weighted latency fell from `275.892` to `30.603` ms | Real SQLite quick; full `NOT RUN` |
| [I](tracks/i_quantum_qml/README.md) | Named quantum algorithms and QML | Grover used fewer queries but more simulator time; classical QML baselines matched or exceeded quantum models | Simulator quick; full `NOT RUN` |
| [J](tracks/j_software_engineering/README.md) | CI test selection/prioritization | Greedy/exact detected 6/6 mutations at the 25% phase budget vs 0/6 alphabetically | Real pytest quick; full `NOT RUN` |

The datasets for A–F, H and I are deterministic synthetic fixtures designed for reproducibility, not production claims. D and J record real local process/test timings. C and I use local CPU quantum simulators only. G is a genuine pinned xv6-riscv build, boot, `usertests` run and benchmark under QEMU.

## Technology and environment

- Ubuntu 26.04 LTS under WSL2; uv-managed CPython 3.11.18
- NumPy 2.3.5, SciPy 1.16.3 and Matplotlib 3.10.7
- CPU-only PyTorch 2.10.0 and PennyLane 0.45.1
- Python standard-library SQLite 3.53.1
- QEMU 10.2.1, RISC-V GCC 14.2.0, binutils 2.45.50 and GDB 17.1 for Track G

Exact package and toolchain details are in [the environment record](docs/environment.md). VS Code is configured to use `.venv/bin/python`; the system Python installation is not modified.

## Install and verify

```bash
uv python install 3.11
uv venv --python 3.11 .venv
uv sync --all-extras --locked
source .venv/bin/activate

python -m optlab list
pytest -q -m 'not slow and not external'
python -m optlab.validate_artifacts --output-dir results
```

The current repository gate is 56 passing fast tests. Artifact validation checks A–J summaries, correctness invariants, and the completed A–F full artifacts.

Run selected quick profiles:

```bash
python -m optlab run --track a --profile quick
MPLCONFIGDIR=/tmp/optlab-matplotlib python -m optlab run --track c --profile quick
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  python -m optlab run --track d --profile quick
```

Full profiles are opt-in. To preserve the primary quick artifacts, write full output to its existing separate directory; for example:

```bash
python -c "from pathlib import Path; from optlab.track_a import run_experiment; print(run_experiment('full', Path('results/a/full')))"
```

Equivalent A–F commands and the external QEMU workflow are listed in [the final implementation handoff](docs/final_handoff.md). Do not use a generic full run to imply G–J evidence: those entrypoints truthfully return `NOT RUN`.

## Repository navigation

- [Assignment requirements coverage](docs/coverage_matrix.md)
- [Final implementation handoff and reproduction commands](docs/final_handoff.md)
- [Raw results and plots](results/)
- [Source implementations](src/optlab/) and [fast tests](tests/)
- [Development environment](docs/environment.md)
- [AI evidence workflow](docs/evidence_workflow.md), [prompt records](prompts/) and [tool register](docs/ai_tools.md)
- [Genuine correction log](docs/failure_log.md) and [two-tool comparison status](docs/tool_comparison.md)
- [Technical-report template](reports/technical_report.md) and [demonstration script](reports/demo.md)

## Limitations and disclosure status

Results come from small educational workloads on one WSL2 host. Timing is sensitive to process startup, caches and host load; simulator measurements are not hardware forecasts. Quantum advantage, physical RISC-V performance, production database behavior and production EV deployment are not claimed.

The work was developed with Codex assistance; the exact model identifier was not exposed and remains `unknown`. Original prompts, revisions, verification notes and commit references are tracked. Sanitized response exports/screenshots, final student review, complete raw evidence for two of the three correction cases, and an actual independent second-tool comparison still require user-supplied evidence. Nothing in this repository substitutes fabricated records for those items.
