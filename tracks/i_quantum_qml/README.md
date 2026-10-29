# I — Named quantum algorithms and QML

Status: **quick simulator profile executed** on 2026-10-29. The full profile is **NOT RUN**. All quantum results use PennyLane 0.45.1 local CPU simulation; no quantum hardware or quantum advantage is claimed. The authoritative Chapter 6 deck remains unavailable, so every algorithm explicitly listed in `plan.md` is covered but additional syllabus-only algorithms cannot yet be reconciled.

## Named circuit demonstrations

Deutsch–Jozsa, Bernstein–Vazirani, Grover, QFT and QPE are assembled directly from gates in `track_i.py`; no algorithm template is used. The manual QFT uses Hadamard, controlled phase and SWAP gates, and its inverse recovers the original basis state. The table reports median simulator execution after one warmup and three timed calls. Gate counts are PennyLane logical/high-level operation counts; `MultiControlledX` and controlled modular unitaries are not decomposed to a hardware-native gate set.

| Algorithm / instance | Qubits | Logical gates | Depth | Oracle calls | Known result | Success probability | Simulator time |
|---|---:|---:|---:|---:|---|---:|---:|
| Deutsch–Jozsa, constant | 4 | 8 | 2 | 1 | constant | 1.0000 | 3.011 ms |
| Deutsch–Jozsa, balanced | 4 | 10 | 5 | 1 | balanced | 1.0000 | 2.892 ms |
| Bernstein–Vazirani `101` | 4 | 10 | 5 | 1 | `101` | 1.0000 | 2.443 ms |
| Grover, target 5 of 8 | 3 | 43 | 21 | 2 | 5 | 0.9453 | 8.034 ms |
| Manual QFT, basis 5 | 3 | 8 | 7 | 0 | inverse recovers 5 | 1.0000 | 3.865 ms |
| QPE, phase 3/8 | 4 | 14 | 10 | 7 powered uses | `011` | 1.0000 | 6.072 ms |
| Compiled Shor, `N=15,a=2` | 7 | 14 | 10 | 7 powered uses | factors 3 and 5 | 0.5000 useful phase | 7.763 ms |

The Shor example is deliberately narrow: a four-qubit work register uses explicit controlled permutation matrices for multiplication by powers of 2 modulo 15. QPE peaks at indices 0, 2, 4 and 6, recovers order 4, and the classical GCD postprocessing returns 3 and 5. This is a compiled educational demonstration, not a scalable implementation of reversible modular exponentiation.

## Grover versus classical search

For target 5 in an eight-item database, Grover uses two oracle calls and returns the target with analytic probability 0.9453125. Ascending classical search actually uses six equality queries for this target and has eight-query worst case. This illustrates `O(sqrt(N))` versus `O(N)` query scaling only; the measured implementation does not show runtime advantage:

| Method | Actual queries | Median local wall time |
|---|---:|---:|
| Grover statevector circuit | 2 | 7.271 ms |
| Python linear search | 6 | 0.0062 ms |

Twenty raw timings are retained. Statevector simulation performs classical amplitude updates and tape processing, so its wall time is neither a hardware forecast nor evidence against the theoretical query bound.

Finite-shot runs produced target fractions 0.922–0.969 at 128 shots and 0.932–0.958 at 1,024 shots. On `default.mixed`, synthetic depolarization after each Grover iteration reduced target probability from 0.9453 at `p=0` to 0.9067, 0.8341 and 0.7359 at `p=0.01`, `0.03` and `0.06`. This is a generic density-matrix noise model, not device calibration.

## Classical simulated annealing

A fixed-seed Metropolis simulated annealer reuses Track B's verified four-node Max-Cut instance. Twenty runs of 120 sweeps all reached the enumerated optimum 6.5 in this tiny case. It is explicitly a **classical annealing simulator**, not quantum annealing or quantum hardware.

## Quantum ML against matched classical models

All models use exactly the same seed-2026 balanced nonlinear dataset, with 24 training and 16 held-out examples. No test example is used for fitting. Labels depend on the sign of `cos(x0)cos(x1)`; this gives a compact nonlinear boundary suited to both circuit and classical nonlinear models.

| Model | Held-out accuracy | Parameters | Training/circuit cost | Time |
|---|---:|---:|---:|---:|
| Quantum fidelity-kernel ridge | 0.8125 | 0 trainable | 660 overlap circuits | 1.867 s |
| Classical RBF-kernel ridge | 0.8750 | 1 fixed hyperparameter | 0 circuits | 0.000174 s |
| Two-qubit variational classifier | 0.8750 | 5 | 6,736 circuit executions / 35 steps | 20.301 s |
| Classical trigonometric logistic regression | 0.9375 | 6 | 29 BFGS iterations | 0.00728 s |

The fidelity kernel is evaluated by actual feature-map/adjoint overlap circuits. The variational classifier uses parameter-shift differentiation and records every loss step. Both quantum models underperformed the appropriate classical comparator and cost much more simulator time; there is no quantum-advantage claim. These are small synthetic held-out results, not broad model-selection evidence.

## Track C reuse and artifacts

Track C remains the source for QAOA, VQE, parameter-shift/QNG/SPSA optimization, and its finite-size barren-plateau study. Track I links those artifacts rather than duplicating them. Track I's separate parameter-shift VQC and noise experiments serve classification and Grover-specific questions.

- Named algorithm results and raw timing: [`algorithms.csv`](../../results/i/algorithms.csv), [`algorithm_timing_raw.csv`](../../results/i/algorithm_timing_raw.csv)
- Search/shot/noise evidence: [`grover_search_timing.csv`](../../results/i/grover_search_timing.csv), [`grover_shots.csv`](../../results/i/grover_shots.csv), [`grover_noise.csv`](../../results/i/grover_noise.csv)
- Annealing: [`annealing_runs.csv`](../../results/i/annealing_runs.csv)
- Identical QML dataset and comparisons: [`qml_dataset.csv`](../../results/i/qml_dataset.csv), [`qml_comparison.csv`](../../results/i/qml_comparison.csv)
- QML histories/predictions: [`vqc_history.csv`](../../results/i/vqc_history.csv), [`kernel_predictions.csv`](../../results/i/kernel_predictions.csv), [`vqc_predictions.csv`](../../results/i/vqc_predictions.csv)
- Machine-readable summary: [`summary.json`](../../results/i/summary.json)

Reproduce:

```bash
MPLCONFIGDIR=/tmp/optlab-matplotlib \
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  python -m optlab run --track i --profile quick
pytest -q tests/test_track_i.py
```

## Limitations

All quantum work is simulator-only and classically tractable. The Shor unitary is compiled for 15, annealing is classical, and the depolarizing channel is synthetic. QML uses only 40 synthetic points and analytic overlap circuits; finite-shot kernel estimation is not run. Grover gate counts are high-level, not fault-tolerant resource estimates. PennyLane warns that device-constructor shots are deprecated, although the recorded finite-shot executions remain valid. Expensive statevector scaling, data loading, barren plateaus (measured in Track C), and the contrast with Track D's real multiprocessing all argue against interpreting these results as practical speedup. Additional taught algorithms remain unknown until the real Chapter 6 deck is supplied.
