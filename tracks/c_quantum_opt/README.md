# C — Variational quantum optimization

Status: **quick and full simulator profiles executed**. The tables below preserve the quick run; separate full artifacts are under [`results/c/full`](../../results/c/full/). Every result is from PennyLane 0.45.1 local CPU simulation; no quantum hardware or quantum advantage is claimed.

## QAOA on Track B's Max-Cut

The actual two-layer QAOA circuit imports Track B's tracked four-node instance and verified Ising mapping. Its cost Hamiltonian is exactly the Track B energy `E=-cut`, including constant `-4`, zero fields, and edge couplings `J_ij=w_ij/2`. An exhaustive basis-state test checks all 16 diagonal Hamiltonian energies against Track B.

COBYLA terminated normally after 160 circuit energy evaluations (0.5603 s). The optimized exact-state expectation cut was `6.142389259`, below the classical exhaustive optimum `6.5`; probability assigned to the two optimal bitstrings `0110` and `1001` was `0.490765`. This small simulated result is evidence of approximation behavior, not speedup or advantage.

Finite-shot sampling used three seeded repeats per shot count:

| Shots | Estimated-energy range | Standard-error range | Optimal-sample fraction range |
|---:|---:|---:|---:|
| 100 | -6.210 to -6.145 | 0.0458–0.0743 | 0.47–0.58 |
| 500 | -6.172 to -6.138 | 0.0247–0.0295 | 0.480–0.502 |
| 2,000 | -6.1605 to -6.14575 | 0.0136–0.0140 | 0.4930–0.5075 |

The observed standard-error reduction is a sampling result; wall time at this scale is dominated by simulator overhead.

## Synthetic noise

`default.mixed` applies an independent depolarizing channel after every mixer rotation in each layer. It is a plausible generic model, not hardware calibration.

| Per-wire/layer probability | Expected cut | Optimal-state probability |
|---:|---:|---:|
| 0.00 | 6.142389 | 0.490765 |
| 0.01 | 5.993743 | 0.462040 |
| 0.03 | 5.721571 | 0.410429 |

## VQE and optimizer comparison

The separate two-qubit VQE Hamiltonian is `H=-Z₀-0.7Z₁+0.3X₀X₁`. Direct matrix diagonalization gives ground energy `-1.726267650`. Parameter-shift, SPSA, and quantum natural gradient start from identical parameters and use comparable budgets near 300 circuit evaluations.

| Method | Evaluations | Energy error | Wall time |
|---|---:|---:|---:|
| Parameter-shift GD | 296 | 1.3111e-5 | 0.3242 s |
| SPSA | 298 | 7.7104e-4 | 0.3138 s |
| QNG | 296 | 1.3574e-5 | 0.3305 s |

The parameter-shift rule is independently checked against central finite differences. QNG uses a documented diagonal Fubini–Study approximation `0.25I` plus `1e-3` damping, not the full metric. Circuit evaluations and wall time are reported separately.

## PQC/QNN hybrid loop

A one-qubit parameterized circuit is trained jointly with a classical scale and bias on six fixed labeled angles. Over 80 Adam steps, measured MSE fell from `0.084293` to `0.061316`; training accuracy was `1.0`, with 2,880 recorded simulator executions and 3.1301 s wall time. This tiny training-set demonstration is not a generalization claim.

## Gradient-variance illustration

Eight seeded random circuits were measured for each width/depth using a global Pauli-Z product cost. At depth 3, gradient variance changed from `0.09318` (2 qubits) to `0.01094` (4) and `0.01069` (6). Across all depths, 6-qubit variance was `0.00801–0.01096`, below the corresponding 2-qubit values `0.09318–0.14623`. Depth trends were non-monotone, so this is only a finite-size barren-plateau illustration, not an asymptotic demonstration.

The initial probe used a parameter that cancelled exactly under a depth-1 parity circuit. That structural-zero artifact was caught before the final run; the tracked experiment uses CZ entanglers and a non-cancelled parameter position.

## Annealer embedding limitation

The logical graph contains triangle `0-1-2`. A four-site path hardware graph has no triangle, so one-to-one placement is impossible: at least one logical variable needs a multi-qubit chain plus a chain-strength penalty. That consumes physical qubits and can distort the logical energy scale. No physical annealer was used.

## Reproduce and artifacts

```bash
source .venv/bin/activate
MPLCONFIGDIR=/tmp/optlab-matplotlib python -m optlab run --track c --profile quick
MPLCONFIGDIR=/tmp/optlab-matplotlib pytest -q tests/test_track_c.py
```

Implementation: `src/optlab/track_c.py`. Summary: [`summary.json`](../../results/c/summary.json). Raw files cover [`QAOA optimization`](../../results/c/qaoa_optimization.csv), [`shots`](../../results/c/qaoa_shots.csv), [`noise`](../../results/c/qaoa_noise.csv), [`optimizer comparison`](../../results/c/optimizer_comparison.csv), [`optimizer histories`](../../results/c/optimizer_histories.csv), [`QNN history`](../../results/c/qnn_history.csv), and [`gradient samples`](../../results/c/barren_plateau_raw.csv). Figures are derived only from these measured files.

## Limitations and deviations

- All circuits ran on `default.qubit` or `default.mixed`, never hardware.
- QAOA underperformed exact enumeration; no quantum advantage is supported.
- The noise model is synthetic and the problem sizes are classically trivial.
- QNG approximates rather than constructs the full quantum metric tensor.
- Eight quick-profile plateau trials per cell give a noisy finite-size estimate; the full profile used the larger configured trial count but remains a finite-size simulation.
- PennyLane emitted a deprecation warning for setting finite shots on device construction; execution and results were unaffected, but a future API migration will be needed.
