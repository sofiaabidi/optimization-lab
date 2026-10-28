# B — Discrete optimization, Max-Cut, and Ising

Status: **quick profile executed** on 2026-10-28. The full profile is implemented but **NOT RUN**. Feature selection remains a syllabus decision open because no authoritative taught-method inventory has been supplied.

## Knapsack formulation

For item decisions `x_i ∈ {0,1}`, maximize `Σ value_i x_i` subject to `Σ weight_i x_i ≤ 33`. Seed 2026 produces 12 fixed items; their weights and values are preserved in `summary.json`. Ratio-greedy is the baseline. Exact alternatives are capacity dynamic programming, fractional-bound branch-and-bound, and SciPy `milp` using its open-source HiGHS backend. Exhaustive enumeration of all 4,096 assignments is an independent oracle.

| Method | Value | Weight | Gap to oracle | Measured wall time |
|---|---:|---:|---:|---:|
| Ratio greedy | 152 | 30 | 1 | 0.0649 ms |
| Dynamic programming | 153 | 32 | 0 | 0.1724 ms |
| Branch-and-bound | 153 | 32 | 0 | 0.1254 ms |
| SciPy/HiGHS MILP | 153 | 32 | 0 | 3.1182 ms |
| Brute-force oracle | 153 | 32 | 0 | 37.2825 ms |

Every returned selection passed the capacity check. These tiny timings are measurements, but not scaling claims; MILP startup dominates here.

## Stable weighted Max-Cut mapping

The four-node, five-edge input is tracked in [`maxcut_instance.json`](maxcut_instance.json) for reuse by Track C. For binary side assignments `x`, the cut is

`C(x) = Σ_(i,j) w_ij (x_i + x_j - 2 x_i x_j)`.

The minimization QUBO uses `E_Q(x)=xᵀQx=-C(x)`: diagonal entries are negative weighted degrees and each symmetric off-diagonal entry is the edge weight. With `x=(1-z)/2`, the recorded Ising form is `constant + h·z + Σ_(i<j) J_ij z_i z_j`, with constant `-4`, zero fields, and `J_ij=w_ij/2` on edges.

Exhaustive verification over all 16 bitstrings found maximum cut `6.5` (complementary optima include `0110` and `1001`), QUBO energy `-6.5`, maximum `|QUBO + cut| = 0`, and maximum `|QUBO - Ising| = 0`. Plain Max-Cut is unconstrained here and uses no constraint penalty.

## Separate constrained penalty example

For values `[5,4,3]` with the real constraint `Σx=1`, the minimized energy is `-v·x + P(Σx-1)²`. Exhaustive results demonstrate why penalty strength matters:

| Penalty `P` | Selected bits | Count | Feasible | Energy |
|---:|---|---:|---|---:|
| 0.5 | 111 | 3 | no | -10 |
| 2.0 | 110 | 2 | no | -7 |
| 6.0 | 100 | 1 | yes | -5 |

This is the constrained QUBO penalty demonstration; it is intentionally separate from unconstrained Max-Cut.

## Reproduce and evidence

```bash
source .venv/bin/activate
python -m optlab run --track b --profile quick
pytest -q tests/test_track_b.py
```

Implementation/API: `src/optlab/track_b.py`. Raw evidence: [`knapsack_raw.csv`](../../results/b/knapsack_raw.csv), [`maxcut_energies.csv`](../../results/b/maxcut_energies.csv), [`maxcut_mapping.json`](../../results/b/maxcut_mapping.json), [`penalty_sweep.csv`](../../results/b/penalty_sweep.csv), [`summary.json`](../../results/b/summary.json), and [`knapsack_values.svg`](../../results/b/knapsack_values.svg).

## Limitations

All correctness claims are for small deterministic instances that permit exhaustive checks. They do not establish large-instance runtime behavior. The full profile was not executed. Feature selection is not silently assumed taught or not taught; it remains unresolved pending authoritative course evidence.
