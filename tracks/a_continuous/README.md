# A — Continuous optimization and foundations

Status: **quick and full profiles executed**. The tables below preserve the original bounded quick measurements; the separate full artifacts are under [`results/a/full`](../../results/a/full/).

## Question and formulation

The common comparison fits a regularized linear model on 96 deterministic synthetic observations with three continuous parameters and seed 2026:

\[
L(w)=\frac{1}{2n}\lVert Xw-y\rVert_2^2+\frac{\lambda}{2}\lVert w\rVert_2^2,\qquad \lambda=0.1.
\]

The variables are unconstrained real weights. The analytic oracle solves `(X.T @ X / n + λI)w = X.T @ y / n`; its objective is `0.3260684948522262`, and the Hessian minimum eigenvalue is `0.8993328866`, so this task is strongly convex. Plain full-batch GD is the baseline. GD, SGD, mini-batch SGD, Momentum, NAG, AdaGrad, RMSProp, Adam, and Newton use this same objective. Gauss–Newton is deliberately evaluated separately on its appropriate nonlinear exponential least-squares problem.

## Measured quick results

All first-order entries use 120 updates. Times are CPU wall time for the optimizer loop only and are not meaningful scaling claims.

| Method | Repeats | Final objective | Objective gap | Time per recorded run |
|---|---:|---:|---:|---:|
| GD baseline | 1 | 0.326068495 | approximately 0 | 3.003 ms |
| Momentum | 1 | 0.326069839 | 1.345e-6 | 3.017 ms |
| NAG | 1 | 0.326068495 | 6.087e-10 | 3.206 ms |
| AdaGrad | 1 | 0.326125377 | 5.688e-5 | 3.384 ms |
| RMSProp | 1 | 0.326547493 | 4.790e-4 | 3.871 ms |
| Adam | 1 | 0.326081848 | 1.335e-5 | 4.250 ms |
| SGD | 3 | mean 0.334525218 ± 0.002903547 SD | raw gaps vary | 5.21–6.38 ms |
| Mini-batch SGD | 3 | mean 0.326539855 ± 0.000601571 SD | raw gaps vary | 6.56–8.49 ms |
| Newton | 1 | 0.326068495 | approximately 0 | 0.196 ms for 3 updates |

Newton's tiny-problem time is not a general superiority claim: it forms/solves a Hessian system and dimension is only three. Gauss–Newton recovered the separate noiseless exponential model parameters `[2.0, -0.8]` with zero recorded parameter error; it is not ranked in the ridge table.

## Foundations and correctness

- Manual ridge gradients agree with PyTorch backward to `4.44e-16` maximum absolute error and central finite differences to `1.02e-10`.
- The Hessian-vector product agrees with a finite-difference gradient oracle to `3.08e-10`. The empirical Fisher diagonal is reported as a positive curvature approximation, not as the exact Hessian.
- On convex but not strongly convex `x^4`, GD reduced the objective from `5.0625` to `0.0034998` in 100 steps. The ridge problem supplies the strongly convex case.
- For `(x²-1)²+0.2x`, stationary points are solved from the derivative polynomial: GD from `-2` reaches the global minimum near `x=-1.02412`, while a start at `2` reaches the worse local minimum near `x=0.973994`.
- `x²-y²` at the origin has zero gradient and Hessian eigenvalues `[-2, 2]`, giving the saddle example. `(x-2.3)²` has continuous optimum `2.3` but enumerated integer optimum `2`, illustrating continuous versus discrete decisions.
- Learning-rate sensitivity includes slow progress at `0.005` and detected divergence at `2.5` after 16 updates. Batch-size and label-noise sweeps are in `sensitivity.csv`.

## Reproduce

```bash
source .venv/bin/activate
python -m optlab run --track a --profile quick
pytest -q tests/test_track_a.py
```

Artifacts: [`raw.csv`](../../results/a/raw.csv), [`histories.csv`](../../results/a/histories.csv), [`sensitivity.csv`](../../results/a/sensitivity.csv), [`summary.json`](../../results/a/summary.json), and [`trajectories.svg`](../../results/a/trajectories.svg). Implementation: `src/optlab/track_a.py`; focused oracles: `tests/test_track_a.py`.

## Limitations

This is a small synthetic CPU experiment. Fixed hyperparameters provide controlled trajectories, not exhaustive tuning. The quick stochastic results have three repeats; the full profile has ten. The noisy-label sweep changes the objective itself, so its absolute losses should not be read as optimizer rankings.
