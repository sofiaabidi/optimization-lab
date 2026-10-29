# E — Campus EV charging allocation

Status: **quick and full profiles executed**. The tables below preserve the quick run; separate full artifacts are under [`results/e/full`](../../results/e/full/). The study uses deterministic synthetic inputs and Python 3.11.18 on the documented WSL2 host; it does not claim results from a deployed charging system.

## Process, variables, and assumptions

A campus operator receives each vehicle's arrival slot, departure slot, requested energy, and maximum charging rate, plus a time-of-use price and campus power limit for every one-hour slot. Uncontrolled first-available charging is feasible on the fixed case but buys too much energy in expensive early slots.

The continuous decision variable is `x[v,t]`, kWh delivered to vehicle `v` in slot `t`. The objective is `min sum_t price[t] * sum_v x[v,t]`.

For every vehicle and slot, `x[v,t]` is zero outside `[arrival, departure)`, is between zero and `max_kW * slot_hours`, total slot energy cannot exceed `facility_kW[t] * slot_hours`, and each vehicle's total must equal its requested energy. The model assumes known forecasts, divisible energy, constant within-slot charging, and no battery tapering, conversion loss, charger-port assignment, demand charge, or uncertainty. These are transparent planning assumptions, not a production dispatch model.

The fixed feasible input has four vehicles, six slots, 20 kWh total demand, a 6 kW facility limit, and prices from 0.10 to 0.40 per kWh. The explicit infeasible input adds `EV-X`, which requests 7 kWh in one slot despite its 3 kW rate limit. Inputs are saved in [`vehicles.csv`](../../results/e/vehicles.csv) and [`slots.csv`](../../results/e/slots.csv).

## Strategy selection

| Strategy | Variables / constraints | Quick problem size | Guarantee and overhead | Hardware / parallelism |
|---|---|---:|---|---|
| First available baseline | Continuous allocations; enforces windows, rate, and remaining facility capacity locally | 24 fixed-case variables | Deterministic and lowest overhead; may be expensive or leave energy unmet | One CPU process; serial |
| Cheapest feasible slot heuristic | Continuous allocations; earliest-deadline vehicles choose currently available slots by price | 24 fixed-case variables | Fast and capacity-safe locally; no global feasibility or optimality guarantee | One CPU process; serial |
| SciPy HiGHS LP | Same continuous variables and all constraints solved jointly | 24 fixed; up to 288 in quick scaling | Global optimum for this linear model when feasible; solver startup and model construction overhead | One local solver invocation; no application-level parallelism requested |

The heuristic and LP are distinct optimization methods. Every returned schedule is passed to a separate validator that checks window, per-vehicle rate, facility capacity, and requested-energy equality. Solver infeasibility is a status, never a zero-energy "feasible" schedule. A separate two-vehicle grid enumeration found objective `3.0`, exactly matching the LP (`0.0` error).

## Fixed-case measurements

Each method received the identical immutable input. Instance generation and artifact output were outside the timed region; five quick repeats are retained in [`benchmark_raw.csv`](../../results/e/benchmark_raw.csv).

| Method | Feasible | Cost | Saving vs baseline | Peak | Peak utilization | Median runtime |
|---|---:|---:|---:|---:|---:|---:|
| First available | yes | 4.48 | — | 6.0 kW | 100% | 0.121 ms |
| Cheapest feasible slot | yes | 3.58 | 20.1% | 6.0 kW | 100% | 0.118 ms |
| Exact LP | yes | 3.40 | 24.1% | 6.0 kW | 100% | 1.190 ms |

Optimization improved energy cost, but did **not** improve peak load: peak utilization remained 100% because peak reduction was not in the objective. The heuristic was 0.18 more expensive than the LP. The LP took roughly ten times the measured scheduler time on this tiny case, although all methods completed in milliseconds.

On the infeasible case, both constructive methods returned `PARTIAL_INFEASIBLE` with 4 kWh unmet. HiGHS returned `INFEASIBLE`; no LP schedule or cost was reported. A partial schedule's low cost is not compared as if it served all demand.

## Scaling and capacity sensitivity

The seeded fleet study used sizes 4, 8, 16, and 24 with the same generator and same inputs per method. Every vehicle has a seeded 3–5 slot window, 2 kW limit, and 2–6 kWh request; campus capacity is `max(6, 0.65 * fleet_size)` kW. Exact-LP median runtime rose from 1.250 ms to 2.312 ms. Its costs were 2.32, 5.03, 10.27, and 14.994. First-available remained feasible at all four sizes but cost more. The greedy cheapest-slot method left 2.0 kWh and 4.4 kWh unmet at sizes 8 and 16, respectively, despite LP feasibility; it therefore has no valid cost comparison at those points.

Reducing the fixed facility capacity to 50% made the model infeasible. At 75%, baseline and LP were feasible, but the cheapest-slot heuristic left 0.5 kWh unmet. At 125%, heuristic and LP tied at cost 3.25; extra exact optimization did not improve the objective. These cases show both where global optimization matters and where its overhead buys no better result.

## Reproduce and artifacts

```bash
source .venv/bin/activate
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  python -m optlab run --track e --profile quick
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  pytest -q tests/test_track_e.py
```

Implementation: `src/optlab/track_e.py`. Summary: [`summary.json`](../../results/e/summary.json). Comparisons: [`comparison.csv`](../../results/e/comparison.csv), [`fleet_scaling.csv`](../../results/e/fleet_scaling.csv), and [`capacity_sensitivity.csv`](../../results/e/capacity_sensitivity.csv). Reproducible allocations: [`schedules.csv`](../../results/e/schedules.csv). Plots: [`cost_comparison.svg`](../../results/e/cost_comparison.svg) and [`lp_scaling.svg`](../../results/e/lp_scaling.svg).

## Limitations

All data are synthetic and perfectly forecast. The LP omits charger assignment, nonlinear charging curves, losses, stochastic arrivals, demand charges, and robustness. Fleet capacity scales by a documented rule, so the timing study is algorithmic sensitivity rather than a forecast for one fixed campus. Short timings vary with host load; raw repeats are retained.
