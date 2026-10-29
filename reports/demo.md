# Demonstration script

This is a concise live-demonstration plan, not measured evidence by itself. Run from the repository root after `uv sync --all-extras --locked` and activation of `.venv`.

## Fast repository gate

```bash
python -m optlab list
pytest -q -m 'not slow and not external'
python -m optlab.validate_artifacts --output-dir results
```

## Representative reproducible experiments

```bash
# A: continuous optimization and gradient/oracle checks
python -m optlab run --track a --profile quick

# B: exact/heuristic knapsack and Max-Cut QUBO/Ising mapping
python -m optlab run --track b --profile quick

# C: simulator-only QAOA/VQE/QNN
MPLCONFIGDIR=/tmp/optlab-matplotlib python -m optlab run --track c --profile quick

# D: real local processes, deque stealing, FedAvg and multi-task methods
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  python -m optlab run --track d --profile quick

# E/F: case-study and compiler optimization
python -m optlab run --track e --profile quick
python -m optlab run --track f --profile quick

# H: real SQLite index selection
python -m optlab run --track h --profile quick

# I: simulator-only named circuits and QML comparison
MPLCONFIGDIR=/tmp/optlab-matplotlib python -m optlab run --track i --profile quick
```

Track G requires its documented external xv6/QEMU preparation and should use the commands in [`tracks/g_xv6/README.md`](../tracks/g_xv6/README.md). Track J's quick run is real but longer because it profiles the suite and executes isolated mutations; use [`tracks/j_software_engineering/README.md`](../tracks/j_software_engineering/README.md) when that evidence is part of the demonstration. Do not describe G–J full profiles as executed.
