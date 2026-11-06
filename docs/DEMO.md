# Assignment 8 — Short Demonstration

**Repository:** [optimization-lab](https://github.com/sofiaabidi/optimization-lab)  
**Main case study:** Track E — Campus EV Charging Optimization

## 1. Problem

The project contains ten optimization experiments (Tracks A–J). For this short demonstration, I use the main case study: planning when electric vehicles should charge on a campus.

Vehicles have different arrival and departure times, energy requirements, and charging limits. The facility also has limited capacity, while electricity prices vary between time slots. **The objective is to minimize electricity cost without violating those constraints.**

## 2. Methods compared

- **First-available baseline:** charge vehicles as soon as capacity is available.
- **Cheapest-slot heuristic:** prefer inexpensive time slots while following the constraints.
- **Linear programming (HiGHS):** optimize the full charging schedule jointly.

Each resulting schedule is checked independently for feasibility.

## 3. Measured result

| Method | Total charging cost | Saving vs baseline |
|---|---:|---:|
| First available | 4.48 | — |
| Cheapest-slot heuristic | 3.58 | 20.1% |
| Linear programming | **3.40** | **24.1%** |

The linear program achieved the lowest cost in the tested case. **Peak facility utilization was still 100%**, because this experiment minimized energy cost, not peak demand. These are simulated-case results, not savings measured at a deployed charging station.

## 4. How to demonstrate

From the repository root, in the configured Python 3.11 environment:

```bash
uv run --no-sync python -m optlab run --track e --profile quick
```

Open [Track E's explanation](https://github.com/sofiaabidi/optimization-lab/tree/main/tracks/e_ev_charging) and its [measured results](https://github.com/sofiaabidi/optimization-lab/tree/main/results/e) to show the baseline-versus-optimized comparison and schedules.

## 5. Key lesson

**Optimization is not just obtaining a smaller number.** We must define the objective, respect constraints, verify correctness, and compare methods fairly. Across the other tracks, some sophisticated methods did not outperform simpler baselines—for example, quantum circuits had simulation overhead and priority scheduling traded throughput for response time.

**Additional project evidence:** [Track-by-track results](https://github.com/sofiaabidi/optimization-lab/tree/main/tracks) · [Technical evidence and reproducibility](https://github.com/sofiaabidi/optimization-lab/blob/main/docs/final_handoff.md)
