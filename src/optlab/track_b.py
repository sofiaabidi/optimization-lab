from __future__ import annotations

import csv
import itertools
import json
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

from .experiment import environment_metadata
from .models import ExperimentResult, RunStatus
from .plotting import write_bar_svg

SEED = 2026
MAXCUT_PATH = Path(__file__).resolve().parents[2] / "tracks" / "b_discrete" / "maxcut_instance.json"


@dataclass(frozen=True)
class KnapsackInstance:
    weights: np.ndarray
    values: np.ndarray
    capacity: int
    seed: int


@dataclass(frozen=True)
class Selection:
    bits: tuple[int, ...]
    value: int
    weight: int

    def feasible(self, capacity: int) -> bool:
        return self.weight <= capacity


def make_knapsack(seed: int = SEED, items: int = 12) -> KnapsackInstance:
    rng = np.random.default_rng(seed)
    weights = rng.integers(2, 16, items, dtype=int)
    values = rng.integers(4, 35, items, dtype=int)
    capacity = int(weights.sum() * 0.35)
    return KnapsackInstance(weights, values, capacity, seed)


def _selection(instance: KnapsackInstance, bits: tuple[int, ...] | list[int] | np.ndarray) -> Selection:
    normalized = tuple(int(value) for value in bits)
    if len(normalized) != len(instance.weights) or any(value not in (0, 1) for value in normalized):
        raise ValueError("selection must contain one binary decision per item")
    return Selection(
        normalized,
        int(instance.values @ np.asarray(normalized)),
        int(instance.weights @ np.asarray(normalized)),
    )


def greedy_knapsack(instance: KnapsackInstance) -> Selection:
    order = sorted(
        range(len(instance.weights)),
        key=lambda index: (instance.values[index] / instance.weights[index], instance.values[index], -index),
        reverse=True,
    )
    bits = [0] * len(instance.weights)
    remaining = instance.capacity
    for index in order:
        if instance.weights[index] <= remaining:
            bits[index] = 1
            remaining -= int(instance.weights[index])
    return _selection(instance, bits)


def brute_force_knapsack(instance: KnapsackInstance) -> Selection:
    best = Selection(tuple(0 for _ in instance.weights), 0, 0)
    for bits in itertools.product((0, 1), repeat=len(instance.weights)):
        candidate = _selection(instance, bits)
        if candidate.feasible(instance.capacity) and (candidate.value, -candidate.weight, candidate.bits) > (
            best.value,
            -best.weight,
            best.bits,
        ):
            best = candidate
    return best


def dynamic_programming_knapsack(instance: KnapsackInstance) -> Selection:
    count = len(instance.weights)
    table = np.zeros((count + 1, instance.capacity + 1), dtype=int)
    for item in range(1, count + 1):
        weight = int(instance.weights[item - 1])
        value = int(instance.values[item - 1])
        table[item] = table[item - 1]
        for capacity in range(weight, instance.capacity + 1):
            table[item, capacity] = max(table[item, capacity], value + table[item - 1, capacity - weight])
    bits = [0] * count
    capacity = instance.capacity
    for item in range(count, 0, -1):
        if table[item, capacity] != table[item - 1, capacity]:
            bits[item - 1] = 1
            capacity -= int(instance.weights[item - 1])
    return _selection(instance, bits)


def branch_and_bound_knapsack(instance: KnapsackInstance) -> Selection:
    order = sorted(range(len(instance.weights)), key=lambda i: instance.values[i] / instance.weights[i], reverse=True)
    best_value = 0
    best_bits = [0] * len(order)

    def upper_bound(position: int, weight: int, value: int) -> float:
        remaining = instance.capacity - weight
        bound = float(value)
        for cursor in range(position, len(order)):
            item = order[cursor]
            item_weight = int(instance.weights[item])
            if item_weight <= remaining:
                remaining -= item_weight
                bound += int(instance.values[item])
            else:
                bound += float(instance.values[item]) * remaining / item_weight
                break
        return bound

    bits = [0] * len(instance.weights)

    def search(position: int, weight: int, value: int) -> None:
        nonlocal best_value, best_bits
        if weight > instance.capacity or upper_bound(position, weight, value) < best_value:
            return
        if position == len(order):
            candidate = _selection(instance, bits)
            incumbent = _selection(instance, best_bits)
            if (candidate.value, -candidate.weight, candidate.bits) > (incumbent.value, -incumbent.weight, incumbent.bits):
                best_value = candidate.value
                best_bits = bits.copy()
            return
        item = order[position]
        bits[item] = 1
        search(position + 1, weight + int(instance.weights[item]), value + int(instance.values[item]))
        bits[item] = 0
        search(position + 1, weight, value)

    search(0, 0, 0)
    return _selection(instance, best_bits)


def milp_knapsack(instance: KnapsackInstance) -> Selection:
    result = milp(
        c=-instance.values.astype(float),
        integrality=np.ones(len(instance.weights)),
        bounds=Bounds(np.zeros(len(instance.weights)), np.ones(len(instance.weights))),
        constraints=LinearConstraint(instance.weights.astype(float), -np.inf, float(instance.capacity)),
        options={"disp": False},
    )
    if not result.success or result.x is None:
        raise RuntimeError(f"SciPy MILP failed: {result.message}")
    return _selection(instance, np.rint(result.x).astype(int))


def timed_selection(function: Callable[[KnapsackInstance], Selection], instance: KnapsackInstance) -> tuple[Selection, float]:
    started = perf_counter()
    result = function(instance)
    return result, perf_counter() - started


def load_maxcut_instance(path: Path = MAXCUT_PATH) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    nodes = int(data["nodes"])
    edges = [(int(i), int(j), float(weight)) for i, j, weight in data["edges"]]
    if nodes < 2 or any(i == j or not (0 <= i < nodes and 0 <= j < nodes) or weight <= 0 for i, j, weight in edges):
        raise ValueError("invalid weighted Max-Cut instance")
    return {**data, "nodes": nodes, "edges": edges}


def cut_value(bits: tuple[int, ...] | list[int], instance: dict[str, Any]) -> float:
    if len(bits) != instance["nodes"] or any(bit not in (0, 1) for bit in bits):
        raise ValueError("Max-Cut assignment must be binary and match node count")
    return float(sum(weight for i, j, weight in instance["edges"] if bits[i] != bits[j]))


def maxcut_qubo(instance: dict[str, Any]) -> np.ndarray:
    matrix = np.zeros((instance["nodes"], instance["nodes"]), dtype=float)
    for i, j, weight in instance["edges"]:
        matrix[i, i] -= weight
        matrix[j, j] -= weight
        matrix[i, j] += weight
        matrix[j, i] += weight
    return matrix


def qubo_energy(bits: tuple[int, ...] | list[int], matrix: np.ndarray) -> float:
    vector = np.asarray(bits, dtype=float)
    return float(vector @ matrix @ vector)


def qubo_to_ising(matrix: np.ndarray) -> tuple[float, np.ndarray, np.ndarray]:
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1] or not np.allclose(matrix, matrix.T):
        raise ValueError("QUBO matrix must be square and symmetric")
    ones = np.ones(matrix.shape[0])
    constant = float(0.25 * ones @ matrix @ ones + 0.25 * np.trace(matrix))
    fields = -0.5 * matrix @ ones
    couplings = np.zeros_like(matrix)
    for i in range(matrix.shape[0]):
        for j in range(i + 1, matrix.shape[0]):
            couplings[i, j] = 0.5 * matrix[i, j]
    return constant, fields, couplings


def ising_energy(bits: tuple[int, ...] | list[int], constant: float, fields: np.ndarray, couplings: np.ndarray) -> float:
    spins = 1.0 - 2.0 * np.asarray(bits, dtype=float)
    pair_energy = sum(couplings[i, j] * spins[i] * spins[j] for i in range(len(spins)) for j in range(i + 1, len(spins)))
    return float(constant + fields @ spins + pair_energy)


def enumerate_maxcut(instance: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    matrix = maxcut_qubo(instance)
    constant, fields, couplings = qubo_to_ising(matrix)
    rows = []
    for bits in itertools.product((0, 1), repeat=instance["nodes"]):
        cut = cut_value(bits, instance)
        qubo = qubo_energy(bits, matrix)
        ising = ising_energy(bits, constant, fields, couplings)
        rows.append(
            {
                "bits": "".join(map(str, bits)),
                "cut_value": cut,
                "qubo_energy": qubo,
                "ising_energy": ising,
                "qubo_plus_cut_error": qubo + cut,
                "qubo_minus_ising_error": qubo - ising,
            }
        )
    optimum = max(rows, key=lambda row: (row["cut_value"], row["bits"]))
    mapping = {
        "convention": "x in {0,1}; z=1-2x; minimize x^T Q x = constant + h.z + sum_{i<j} J_ij z_i z_j = -cut",
        "qubo_matrix": matrix.tolist(),
        "ising_constant": constant,
        "ising_fields": fields.tolist(),
        "ising_couplings_upper": couplings.tolist(),
        "optimum": optimum,
        "max_abs_qubo_plus_cut_error": max(abs(row["qubo_plus_cut_error"]) for row in rows),
        "max_abs_qubo_minus_ising_error": max(abs(row["qubo_minus_ising_error"]) for row in rows),
    }
    return rows, mapping


def cardinality_penalty_demo() -> list[dict[str, Any]]:
    values = np.array([5.0, 4.0, 3.0])
    required_count = 1
    rows = []
    for penalty in (0.5, 2.0, 6.0):
        candidates = []
        for bits in itertools.product((0, 1), repeat=len(values)):
            vector = np.asarray(bits)
            base_value = float(values @ vector)
            violation = int(vector.sum() - required_count)
            energy = -base_value + penalty * violation**2
            candidates.append((energy, bits, base_value, violation))
        energy, bits, base_value, violation = min(candidates, key=lambda item: (item[0], item[1]))
        rows.append(
            {
                "penalty": penalty,
                "selected_bits": "".join(map(str, bits)),
                "selected_count": sum(bits),
                "base_value": base_value,
                "violation": violation,
                "feasible_exactly_one": violation == 0,
                "penalized_energy": energy,
            }
        )
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def run_experiment(profile: str = "quick", output_dir: Path | None = None) -> ExperimentResult:
    if profile not in {"quick", "full"}:
        raise ValueError("profile must be quick or full")
    started = perf_counter()
    output_dir = output_dir or Path("results/b")
    output_dir.mkdir(parents=True, exist_ok=True)
    instance = make_knapsack(items=12 if profile == "quick" else 18)
    methods = {
        "greedy_ratio": greedy_knapsack,
        "dynamic_programming": dynamic_programming_knapsack,
        "branch_and_bound": branch_and_bound_knapsack,
        "scipy_milp": milp_knapsack,
        "brute_force_oracle": brute_force_knapsack,
    }
    measured: dict[str, tuple[Selection, float]] = {
        name: timed_selection(function, instance) for name, function in methods.items()
    }
    oracle_value = measured["brute_force_oracle"][0].value
    knapsack_rows = []
    for name, (selection, duration) in measured.items():
        knapsack_rows.append(
            {
                "method": name,
                "selected_bits": "".join(map(str, selection.bits)),
                "value": selection.value,
                "weight": selection.weight,
                "capacity": instance.capacity,
                "feasible": selection.feasible(instance.capacity),
                "optimality_gap": oracle_value - selection.value,
                "duration_seconds": duration,
            }
        )

    maxcut_instance = load_maxcut_instance()
    maxcut_rows, mapping = enumerate_maxcut(maxcut_instance)
    penalty_rows = cardinality_penalty_demo()
    exact_methods = ["dynamic_programming", "branch_and_bound", "scipy_milp"]
    exact_agreement = all(measured[name][0].value == oracle_value for name in exact_methods)
    summary = {
        "profile": profile,
        "seed": instance.seed,
        "environment": environment_metadata(),
        "knapsack": {
            "weights": instance.weights.tolist(),
            "values": instance.values.tolist(),
            "capacity": instance.capacity,
            "oracle_value": oracle_value,
            "exact_methods_match_oracle": exact_agreement,
        },
        "maxcut": {
            "instance_path": "tracks/b_discrete/maxcut_instance.json",
            "nodes": maxcut_instance["nodes"],
            "edges": maxcut_instance["edges"],
            **mapping,
        },
        "penalty_demo": penalty_rows,
        "feature_selection_status": "SYLLABUS DECISION OPEN — no authoritative taught-method inventory supplied",
        "full_profile_status": "DONE" if profile == "full" else "NOT RUN",
        "limitations": [
            "Small deterministic instances permit exhaustive correctness checks but do not establish large-instance scaling.",
            "SciPy MILP startup overhead dominates this tiny benchmark.",
            "The cardinality example demonstrates a penalty threshold; plain Max-Cut here is unconstrained and has no penalty term.",
        ],
    }
    _write_csv(output_dir / "knapsack_raw.csv", knapsack_rows)
    _write_csv(output_dir / "maxcut_energies.csv", maxcut_rows)
    _write_csv(output_dir / "penalty_sweep.csv", penalty_rows)
    (output_dir / "maxcut_mapping.json").write_text(json.dumps(mapping, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_bar_svg(
        [row["method"].replace("_", " ") for row in knapsack_rows],
        [float(row["value"]) for row in knapsack_rows],
        output_dir / "knapsack_values.svg",
        "Track B knapsack objective by method",
    )
    return ExperimentResult(
        track="b",
        profile=profile,
        status=RunStatus.DONE,
        method="knapsack-maxcut-penalty",
        objective=float(oracle_value),
        duration_seconds=perf_counter() - started,
        seed=instance.seed,
        message=f"wrote measured Track B artifacts to {output_dir}",
        metrics={
            "knapsack_oracle_value": oracle_value,
            "exact_methods_match_oracle": exact_agreement,
            "maxcut_optimum": mapping["optimum"]["cut_value"],
            "maxcut_energy_max_error": mapping["max_abs_qubo_minus_ising_error"],
        },
        metadata=environment_metadata(),
    )
