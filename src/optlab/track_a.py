from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np

from .experiment import environment_metadata
from .models import ExperimentResult, RunStatus

SEED = 2026


@dataclass(frozen=True)
class RidgeProblem:
    x: np.ndarray
    y: np.ndarray
    regularization: float

    def loss(self, weights: np.ndarray) -> float:
        residual = self.x @ weights - self.y
        return float(0.5 * np.mean(residual**2) + 0.5 * self.regularization * weights @ weights)

    def gradient(self, weights: np.ndarray, indices: np.ndarray | None = None) -> np.ndarray:
        x = self.x if indices is None else self.x[indices]
        y = self.y if indices is None else self.y[indices]
        return x.T @ (x @ weights - y) / len(x) + self.regularization * weights

    @property
    def hessian(self) -> np.ndarray:
        return self.x.T @ self.x / len(self.x) + self.regularization * np.eye(self.x.shape[1])

    @property
    def optimum(self) -> np.ndarray:
        return np.linalg.solve(self.hessian, self.x.T @ self.y / len(self.x))


@dataclass
class OptimizerRun:
    method: str
    repeat: int
    weights: np.ndarray
    history: list[float]
    duration_seconds: float
    converged: bool


def make_ridge_problem(seed: int = SEED, noise_std: float = 0.2, samples: int = 96) -> RidgeProblem:
    rng = np.random.default_rng(seed)
    x = rng.normal(size=(samples, 3))
    true_weights = np.array([1.5, -2.0, 0.75])
    y = x @ true_weights + rng.normal(scale=noise_std, size=samples)
    return RidgeProblem(x=x, y=y, regularization=0.1)


def finite_difference_gradient(problem: RidgeProblem, weights: np.ndarray, epsilon: float = 1e-6) -> np.ndarray:
    estimate = np.empty_like(weights, dtype=float)
    for index in range(len(weights)):
        direction = np.zeros_like(weights, dtype=float)
        direction[index] = epsilon
        estimate[index] = (problem.loss(weights + direction) - problem.loss(weights - direction)) / (2 * epsilon)
    return estimate


def run_first_order(
    problem: RidgeProblem,
    method: str,
    *,
    learning_rate: float,
    steps: int,
    seed: int,
    batch_size: int | None = None,
    repeat_index: int = 0,
) -> OptimizerRun:
    supported = {"gd", "sgd", "mini_batch_sgd", "momentum", "nag", "adagrad", "rmsprop", "adam"}
    if method not in supported:
        raise ValueError(f"unknown first-order method: {method}")
    rng = np.random.default_rng(seed)
    weights = np.zeros(problem.x.shape[1], dtype=float)
    velocity = np.zeros_like(weights)
    accumulator = np.zeros_like(weights)
    second_moment = np.zeros_like(weights)
    first_moment = np.zeros_like(weights)
    history = [problem.loss(weights)]
    started = perf_counter()
    for step in range(1, steps + 1):
        indices = None
        if method == "sgd":
            indices = rng.integers(0, len(problem.x), size=1)
        elif method == "mini_batch_sgd":
            size = batch_size or min(12, len(problem.x))
            indices = rng.choice(len(problem.x), size=size, replace=False)

        if method == "nag":
            lookahead = weights - 0.9 * learning_rate * velocity
            gradient = problem.gradient(lookahead)
        else:
            gradient = problem.gradient(weights, indices)

        if method in {"gd", "sgd", "mini_batch_sgd"}:
            weights -= learning_rate * gradient
        elif method in {"momentum", "nag"}:
            velocity = 0.9 * velocity + gradient
            weights -= learning_rate * velocity
        elif method == "adagrad":
            accumulator += gradient**2
            weights -= learning_rate * gradient / (np.sqrt(accumulator) + 1e-8)
        elif method == "rmsprop":
            second_moment = 0.9 * second_moment + 0.1 * gradient**2
            weights -= learning_rate * gradient / (np.sqrt(second_moment) + 1e-8)
        elif method == "adam":
            first_moment = 0.9 * first_moment + 0.1 * gradient
            second_moment = 0.999 * second_moment + 0.001 * gradient**2
            corrected_first = first_moment / (1 - 0.9**step)
            corrected_second = second_moment / (1 - 0.999**step)
            weights -= learning_rate * corrected_first / (np.sqrt(corrected_second) + 1e-8)

        objective = problem.loss(weights)
        history.append(objective)
        if not math.isfinite(objective) or objective > 1e12:
            break
    duration = perf_counter() - started
    optimum_loss = problem.loss(problem.optimum)
    converged = math.isfinite(history[-1]) and history[-1] - optimum_loss < 2e-2
    return OptimizerRun(method, repeat_index, weights, history, duration, converged)


def run_newton(problem: RidgeProblem, steps: int = 3) -> OptimizerRun:
    weights = np.zeros(problem.x.shape[1], dtype=float)
    history = [problem.loss(weights)]
    started = perf_counter()
    for _ in range(steps):
        weights -= np.linalg.solve(problem.hessian, problem.gradient(weights))
        history.append(problem.loss(weights))
    return OptimizerRun("newton", 0, weights, history, perf_counter() - started, True)


def gauss_newton_demo(steps: int = 12) -> dict[str, Any]:
    x = np.linspace(0.0, 1.0, 30)
    true_parameters = np.array([2.0, -0.8])
    y = true_parameters[0] * np.exp(true_parameters[1] * x)
    parameters = np.array([1.0, -0.2])
    history: list[float] = []
    started = perf_counter()
    for _ in range(steps):
        prediction = parameters[0] * np.exp(parameters[1] * x)
        residual = prediction - y
        history.append(float(0.5 * np.mean(residual**2)))
        jacobian = np.column_stack((np.exp(parameters[1] * x), parameters[0] * x * np.exp(parameters[1] * x)))
        step = np.linalg.solve(jacobian.T @ jacobian + 1e-8 * np.eye(2), jacobian.T @ residual)
        parameters -= step
    residual = parameters[0] * np.exp(parameters[1] * x) - y
    history.append(float(0.5 * np.mean(residual**2)))
    return {
        "method": "gauss_newton",
        "parameters": parameters.tolist(),
        "true_parameters": true_parameters.tolist(),
        "parameter_error_l2": float(np.linalg.norm(parameters - true_parameters)),
        "history": history,
        "duration_seconds": perf_counter() - started,
    }


def backpropagation_check(problem: RidgeProblem) -> dict[str, float]:
    import torch

    weights_np = np.array([0.3, -0.4, 0.2])
    x = torch.tensor(problem.x, dtype=torch.float64)
    y = torch.tensor(problem.y, dtype=torch.float64)
    weights = torch.tensor(weights_np, dtype=torch.float64, requires_grad=True)
    loss = 0.5 * torch.mean((x @ weights - y) ** 2) + 0.5 * problem.regularization * weights @ weights
    loss.backward()
    autograd = weights.grad.detach().numpy()
    manual = problem.gradient(weights_np)
    finite_difference = finite_difference_gradient(problem, weights_np)
    return {
        "manual_vs_autograd_max_abs": float(np.max(np.abs(manual - autograd))),
        "manual_vs_finite_difference_max_abs": float(np.max(np.abs(manual - finite_difference))),
        "loss": float(loss.detach()),
    }


def curvature_check(problem: RidgeProblem) -> dict[str, Any]:
    weights = np.array([0.3, -0.4, 0.2])
    vector = np.array([0.5, -1.0, 0.25])
    epsilon = 1e-6
    exact_hvp = problem.hessian @ vector
    finite_hvp = (problem.gradient(weights + epsilon * vector) - problem.gradient(weights - epsilon * vector)) / (2 * epsilon)
    residual = problem.x @ weights - problem.y
    per_sample_gradients = residual[:, None] * problem.x + problem.regularization * weights
    empirical_fisher_diagonal = np.mean(per_sample_gradients**2, axis=0)
    return {
        "hessian_diagonal": np.diag(problem.hessian).tolist(),
        "empirical_fisher_diagonal": empirical_fisher_diagonal.tolist(),
        "hvp_max_abs_error": float(np.max(np.abs(exact_hvp - finite_hvp))),
        "note": "Empirical Fisher diagonal is a positive curvature approximation; it is not asserted equal to the Hessian.",
    }


def landscape_examples() -> dict[str, Any]:
    polynomial = np.array([4.0, 0.0, -4.0, 0.2])
    stationary = sorted(float(root.real) for root in np.roots(polynomial) if abs(root.imag) < 1e-10)

    def nonconvex(x: float) -> float:
        return (x * x - 1) ** 2 + 0.2 * x

    classified = []
    for point in stationary:
        second = 12 * point * point - 4
        classified.append({"x": point, "value": nonconvex(point), "type": "minimum" if second > 0 else "maximum"})
    minima = [item for item in classified if item["type"] == "minimum"]
    global_minimum = min(minima, key=lambda item: item["value"])
    for item in minima:
        item["scope"] = "global" if item is global_minimum else "local"

    def descend(start: float, learning_rate: float = 0.03, steps: int = 150) -> tuple[float, float]:
        value = start
        for _ in range(steps):
            value -= learning_rate * (4 * value**3 - 4 * value + 0.2)
        return value, nonconvex(value)

    convex_value = 1.5
    convex_history = [convex_value**4]
    for _ in range(100):
        convex_value -= 0.02 * 4 * convex_value**3
        convex_history.append(convex_value**4)

    return {
        "continuous_vs_discrete": {
            "objective": "(x - 2.3)^2",
            "continuous_optimum": 2.3,
            "integer_optimum_by_enumeration": min(range(-5, 6), key=lambda x: (x - 2.3) ** 2),
        },
        "convex_not_strongly_convex": {
            "objective": "x^4",
            "hessian_at_optimum": 0.0,
            "gd_start_objective": convex_history[0],
            "gd_final_x": convex_value,
            "gd_final_objective": convex_history[-1],
            "gd_steps": 100,
        },
        "strongly_convex": {"ridge_hessian_min_eigenvalue": None},
        "nonconvex_stationary_points": classified,
        "nonconvex_gd_from_negative": descend(-2.0),
        "nonconvex_gd_from_positive": descend(2.0),
        "saddle": {"objective": "x^2-y^2", "point": [0.0, 0.0], "gradient": [0.0, 0.0], "hessian_eigenvalues": [-2.0, 2.0]},
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_trajectory_svg(path: Path, histories: dict[str, list[float]], optimum: float) -> None:
    width, height, left, top = 760, 420, 70, 35
    plot_width, plot_height = 650, 320
    colors = ["#4472c4", "#ed7d31", "#70ad47", "#a5a5a5", "#ffc000", "#5b9bd5", "#c55a11", "#8064a2", "#264478"]
    all_logs = [math.log10(max(value - optimum, 1e-14)) for values in histories.values() for value in values]
    minimum, maximum = min(all_logs), max(all_logs)
    span = maximum - minimum or 1.0
    longest = max(len(values) for values in histories.values()) - 1 or 1
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="380" y="20" text-anchor="middle">Track A quick run: objective gap trajectories</text>',
        f'<line x1="{left}" y1="{top + plot_height}" x2="{left + plot_width}" y2="{top + plot_height}" stroke="black"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_height}" stroke="black"/>',
    ]
    for index, (method, values) in enumerate(histories.items()):
        points = []
        for step, value in enumerate(values):
            x = left + plot_width * step / longest
            logged = math.log10(max(value - optimum, 1e-14))
            y = top + plot_height * (maximum - logged) / span
            points.append(f"{x:.2f},{y:.2f}")
        color = colors[index % len(colors)]
        parts.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="1.5"/>')
        parts.append(f'<text x="{left + plot_width + 8}" y="{top + 15 * (index + 1)}" fill="{color}" font-size="11">{method}</text>')
    parts.extend([
        f'<text x="{left + plot_width / 2}" y="{height - 20}" text-anchor="middle">iteration</text>',
        f'<text x="15" y="{top + plot_height / 2}" transform="rotate(-90 15 {top + plot_height / 2})" text-anchor="middle">log10(objective gap)</text>',
        "</svg>",
    ])
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def run_experiment(profile: str = "quick", output_dir: Path | None = None) -> ExperimentResult:
    if profile not in {"quick", "full"}:
        raise ValueError("profile must be quick or full")
    total_started = perf_counter()
    output_dir = output_dir or Path("results/a")
    output_dir.mkdir(parents=True, exist_ok=True)
    problem = make_ridge_problem()
    optimum = problem.optimum
    optimum_loss = problem.loss(optimum)
    steps = 120 if profile == "quick" else 400
    repeats = 3 if profile == "quick" else 10
    configurations = {
        "gd": 0.2,
        "momentum": 0.08,
        "nag": 0.08,
        "adagrad": 0.2,
        "rmsprop": 0.03,
        "adam": 0.05,
    }
    runs: list[OptimizerRun] = []
    for method, learning_rate in configurations.items():
        runs.append(run_first_order(problem, method, learning_rate=learning_rate, steps=steps, seed=SEED))
    for method, learning_rate, batch_size in (("sgd", 0.03, 1), ("mini_batch_sgd", 0.08, 12)):
        for repeat_index in range(repeats):
            runs.append(
                run_first_order(
                    problem,
                    method,
                    learning_rate=learning_rate,
                    steps=steps,
                    seed=SEED + repeat_index,
                    batch_size=batch_size,
                    repeat_index=repeat_index,
                )
            )
    runs.append(run_newton(problem))

    raw_rows = []
    history_rows = []
    for run in runs:
        raw_rows.append(
            {
                "method": run.method,
                "repeat": run.repeat,
                "iterations": len(run.history) - 1,
                "final_objective": run.history[-1],
                "objective_gap": run.history[-1] - optimum_loss,
                "distance_to_optimum_l2": float(np.linalg.norm(run.weights - optimum)),
                "duration_seconds": run.duration_seconds,
                "converged": run.converged,
            }
        )
        for step, objective in enumerate(run.history):
            history_rows.append({"method": run.method, "repeat": run.repeat, "step": step, "objective": objective})

    sensitivity_rows = []
    for learning_rate in (0.005, 0.05, 0.5, 2.5):
        run = run_first_order(problem, "gd", learning_rate=learning_rate, steps=80, seed=SEED)
        sensitivity_rows.append({"factor": "learning_rate", "value": learning_rate, "iterations": len(run.history) - 1, "final_objective": run.history[-1], "converged": run.converged})
    for batch_size in (1, 8, 32):
        run = run_first_order(problem, "mini_batch_sgd", learning_rate=0.05, steps=80, seed=SEED, batch_size=batch_size)
        sensitivity_rows.append({"factor": "batch_size", "value": batch_size, "iterations": len(run.history) - 1, "final_objective": run.history[-1], "converged": run.converged})
    for noise_std in (0.0, 0.2, 0.8):
        noisy_problem = make_ridge_problem(noise_std=noise_std)
        run = run_first_order(noisy_problem, "gd", learning_rate=0.2, steps=80, seed=SEED)
        sensitivity_rows.append({"factor": "label_noise_std", "value": noise_std, "iterations": len(run.history) - 1, "final_objective": run.history[-1], "converged": run.converged})

    backprop = backpropagation_check(problem)
    curvature = curvature_check(problem)
    landscapes = landscape_examples()
    landscapes["strongly_convex"]["ridge_hessian_min_eigenvalue"] = float(np.linalg.eigvalsh(problem.hessian).min())
    gauss_newton = gauss_newton_demo()
    stochastic_summary = {}
    for method in ("sgd", "mini_batch_sgd"):
        values = np.array([row["final_objective"] for row in raw_rows if row["method"] == method])
        stochastic_summary[method] = {
            "repeats": len(values),
            "final_objective_mean": float(values.mean()),
            "final_objective_std": float(values.std(ddof=1)),
            "final_objective_min": float(values.min()),
            "final_objective_max": float(values.max()),
        }
    summary = {
        "profile": profile,
        "seed": SEED,
        "dataset": {"samples": len(problem.x), "features": problem.x.shape[1], "label_noise_std": 0.2, "regularization": problem.regularization},
        "environment": environment_metadata(),
        "analytic_optimum": optimum.tolist(),
        "analytic_optimum_objective": optimum_loss,
        "gradient_checks": backprop,
        "curvature": curvature,
        "gauss_newton": gauss_newton,
        "landscapes": landscapes,
        "stochastic_repeats": repeats,
        "stochastic_summary": stochastic_summary,
        "full_profile_status": "DONE" if profile == "full" else "NOT RUN",
        "limitations": [
            "Tiny synthetic CPU problem; timings do not predict large-model performance.",
            "Gauss-Newton uses a separate nonlinear least-squares objective and is not ranked against ridge methods.",
            "Empirical Fisher diagonal is demonstrated only as an approximation.",
        ],
    }
    _write_csv(output_dir / "raw.csv", raw_rows)
    _write_csv(output_dir / "histories.csv", history_rows)
    _write_csv(output_dir / "sensitivity.csv", sensitivity_rows)
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    representative = {run.method: run.history for run in runs if run.repeat == 0}
    _write_trajectory_svg(output_dir / "trajectories.svg", representative, optimum_loss)
    best = min(row["final_objective"] for row in raw_rows)
    return ExperimentResult(
        track="a",
        profile=profile,
        status=RunStatus.DONE,
        method="continuous-optimizer-comparison",
        objective=best,
        duration_seconds=perf_counter() - total_started,
        seed=SEED,
        message=f"wrote measured Track A artifacts to {output_dir}",
        metrics={"analytic_optimum_objective": optimum_loss, "runs": len(runs), "stochastic_repeats": repeats},
        metadata=environment_metadata(),
    )
