from __future__ import annotations

import csv
import itertools
import json
from dataclasses import dataclass, replace
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

import numpy as np
from scipy.optimize import linprog

from .experiment import environment_metadata
from .models import ExperimentResult, RunStatus
from .plotting import write_bar_svg

SEED = 2026
TOLERANCE = 1e-7


@dataclass(frozen=True)
class Vehicle:
    vehicle_id: str
    arrival_slot: int
    departure_slot: int
    energy_kwh: float
    max_kw: float


@dataclass(frozen=True)
class ChargingInstance:
    name: str
    prices_per_kwh: np.ndarray
    facility_kw: np.ndarray
    vehicles: tuple[Vehicle, ...]
    slot_hours: float = 1.0
    seed: int = SEED

    @property
    def slot_count(self) -> int:
        return len(self.prices_per_kwh)


@dataclass(frozen=True)
class ScheduleCheck:
    feasible: bool
    unmet_energy_kwh: float
    peak_kw: float
    peak_utilization: float
    max_capacity_violation_kwh: float
    max_vehicle_rate_violation_kwh: float
    max_window_violation_kwh: float
    max_energy_error_kwh: float


@dataclass(frozen=True)
class ScheduleResult:
    method: str
    status: str
    schedule_kwh: np.ndarray | None
    runtime_seconds: float
    solver_message: str = ""


def _validate_instance(instance: ChargingInstance) -> None:
    slots = instance.slot_count
    if slots < 1 or instance.facility_kw.shape != (slots,):
        raise ValueError("price and facility arrays must be non-empty and have equal length")
    if instance.slot_hours <= 0 or np.any(instance.prices_per_kwh < 0) or np.any(instance.facility_kw < 0):
        raise ValueError("duration must be positive and prices/capacities non-negative")
    identifiers: set[str] = set()
    for vehicle in instance.vehicles:
        if vehicle.vehicle_id in identifiers:
            raise ValueError("vehicle identifiers must be unique")
        identifiers.add(vehicle.vehicle_id)
        if not (0 <= vehicle.arrival_slot < vehicle.departure_slot <= slots):
            raise ValueError(f"invalid charging window for {vehicle.vehicle_id}")
        if vehicle.energy_kwh <= 0 or vehicle.max_kw <= 0:
            raise ValueError("vehicle energy and charge rate must be positive")


def make_feasible_instance() -> ChargingInstance:
    instance = ChargingInstance(
        name="campus_feasible",
        prices_per_kwh=np.array([0.36, 0.30, 0.12, 0.10, 0.22, 0.40]),
        facility_kw=np.full(6, 6.0),
        vehicles=(
            Vehicle("EV-A", 0, 3, 4.0, 2.0),
            Vehicle("EV-B", 0, 4, 6.0, 2.0),
            Vehicle("EV-C", 1, 5, 5.0, 2.0),
            Vehicle("EV-D", 2, 6, 5.0, 2.0),
        ),
    )
    _validate_instance(instance)
    return instance


def make_infeasible_instance() -> ChargingInstance:
    feasible = make_feasible_instance()
    instance = replace(
        feasible,
        name="campus_infeasible",
        vehicles=feasible.vehicles + (Vehicle("EV-X", 4, 5, 7.0, 3.0),),
    )
    _validate_instance(instance)
    return instance


def make_fleet_instance(size: int, seed: int = SEED) -> ChargingInstance:
    if size < 1:
        raise ValueError("fleet size must be positive")
    rng = np.random.default_rng(seed + size)
    slots = 12
    vehicles = []
    for index in range(size):
        arrival = int(rng.integers(0, 8))
        departure = min(slots, arrival + int(rng.integers(3, 6)))
        max_kw = 2.0
        maximum = int(max_kw * (departure - arrival))
        energy = float(rng.integers(2, min(6, maximum) + 1))
        vehicles.append(Vehicle(f"EV-{index:03d}", arrival, departure, energy, max_kw))
    instance = ChargingInstance(
        name=f"fleet_{size}",
        prices_per_kwh=np.array([0.28, 0.25, 0.22, 0.18, 0.13, 0.10, 0.12, 0.17, 0.24, 0.31, 0.36, 0.30]),
        facility_kw=np.full(slots, max(6.0, 0.65 * size)),
        vehicles=tuple(vehicles),
        seed=seed,
    )
    _validate_instance(instance)
    return instance


def verify_schedule(
    instance: ChargingInstance,
    schedule_kwh: np.ndarray,
    tolerance: float = TOLERANCE,
) -> ScheduleCheck:
    _validate_instance(instance)
    expected = (len(instance.vehicles), instance.slot_count)
    schedule = np.asarray(schedule_kwh, dtype=float)
    if schedule.shape != expected or not np.all(np.isfinite(schedule)):
        raise ValueError(f"schedule must be a finite array with shape {expected}")

    negative_violation = float(max(0.0, -float(np.min(schedule, initial=0.0))))
    window_violation = negative_violation
    rate_violation = negative_violation
    energy_errors = []
    unmet = 0.0
    for row, vehicle in zip(schedule, instance.vehicles, strict=True):
        allowed = np.zeros(instance.slot_count, dtype=bool)
        allowed[vehicle.arrival_slot : vehicle.departure_slot] = True
        window_violation = max(window_violation, float(np.max(np.abs(row[~allowed]), initial=0.0)))
        slot_limit = vehicle.max_kw * instance.slot_hours
        rate_violation = max(rate_violation, float(np.max(row[allowed] - slot_limit, initial=0.0)))
        delivered = float(np.sum(row))
        error = abs(delivered - vehicle.energy_kwh)
        energy_errors.append(error)
        unmet += max(0.0, vehicle.energy_kwh - delivered)

    slot_energy_limit = instance.facility_kw * instance.slot_hours
    slot_energy = np.sum(schedule, axis=0)
    capacity_violation = float(np.max(slot_energy - slot_energy_limit, initial=0.0))
    peak_kw = float(np.max(slot_energy, initial=0.0) / instance.slot_hours)
    positive_capacity = instance.facility_kw > tolerance
    utilization = (
        float(np.max(slot_energy[positive_capacity] / slot_energy_limit[positive_capacity], initial=0.0))
        if np.any(positive_capacity)
        else 0.0
    )
    max_energy_error = max(energy_errors, default=0.0)
    feasible = max(capacity_violation, rate_violation, window_violation, max_energy_error) <= tolerance
    return ScheduleCheck(
        feasible=feasible,
        unmet_energy_kwh=unmet,
        peak_kw=peak_kw,
        peak_utilization=utilization,
        max_capacity_violation_kwh=max(0.0, capacity_violation),
        max_vehicle_rate_violation_kwh=max(0.0, rate_violation),
        max_window_violation_kwh=max(0.0, window_violation),
        max_energy_error_kwh=max_energy_error,
    )


def schedule_cost(instance: ChargingInstance, schedule_kwh: np.ndarray) -> float:
    return float(instance.prices_per_kwh @ np.sum(schedule_kwh, axis=0))


def _greedy_schedule(instance: ChargingInstance, cheapest: bool) -> np.ndarray:
    schedule = np.zeros((len(instance.vehicles), instance.slot_count), dtype=float)
    remaining_capacity = instance.facility_kw * instance.slot_hours
    vehicle_order = sorted(
        range(len(instance.vehicles)),
        key=lambda index: (
            instance.vehicles[index].departure_slot if cheapest else instance.vehicles[index].arrival_slot,
            instance.vehicles[index].arrival_slot,
            instance.vehicles[index].vehicle_id,
        ),
    )
    for vehicle_index in vehicle_order:
        vehicle = instance.vehicles[vehicle_index]
        slots = list(range(vehicle.arrival_slot, vehicle.departure_slot))
        if cheapest:
            slots.sort(key=lambda slot: (instance.prices_per_kwh[slot], slot))
        remaining_energy = vehicle.energy_kwh
        for slot in slots:
            assigned = min(remaining_energy, vehicle.max_kw * instance.slot_hours, remaining_capacity[slot])
            if assigned > 0:
                schedule[vehicle_index, slot] = assigned
                remaining_capacity[slot] -= assigned
                remaining_energy -= assigned
            if remaining_energy <= TOLERANCE:
                break
    return schedule


def first_available_schedule(instance: ChargingInstance) -> ScheduleResult:
    started = perf_counter()
    schedule = _greedy_schedule(instance, cheapest=False)
    check = verify_schedule(instance, schedule)
    return ScheduleResult(
        method="first_available",
        status="FEASIBLE" if check.feasible else "PARTIAL_INFEASIBLE",
        schedule_kwh=schedule,
        runtime_seconds=perf_counter() - started,
        solver_message="deterministic arrival-order first-available allocation",
    )


def cheapest_slot_schedule(instance: ChargingInstance) -> ScheduleResult:
    started = perf_counter()
    schedule = _greedy_schedule(instance, cheapest=True)
    check = verify_schedule(instance, schedule)
    return ScheduleResult(
        method="cheapest_feasible_slot",
        status="FEASIBLE" if check.feasible else "PARTIAL_INFEASIBLE",
        schedule_kwh=schedule,
        runtime_seconds=perf_counter() - started,
        solver_message="earliest-deadline vehicles assigned to available slots in price order",
    )


def exact_lp_schedule(instance: ChargingInstance) -> ScheduleResult:
    _validate_instance(instance)
    started = perf_counter()
    vehicle_count, slot_count = len(instance.vehicles), instance.slot_count
    variable_count = vehicle_count * slot_count
    objective = np.tile(instance.prices_per_kwh, vehicle_count)
    capacity_matrix = np.zeros((slot_count, variable_count))
    for slot in range(slot_count):
        capacity_matrix[slot, slot::slot_count] = 1.0
    energy_matrix = np.zeros((vehicle_count, variable_count))
    bounds = []
    for vehicle_index, vehicle in enumerate(instance.vehicles):
        energy_matrix[vehicle_index, vehicle_index * slot_count : (vehicle_index + 1) * slot_count] = 1.0
        for slot in range(slot_count):
            upper = vehicle.max_kw * instance.slot_hours if vehicle.arrival_slot <= slot < vehicle.departure_slot else 0.0
            bounds.append((0.0, upper))
    result = linprog(
        c=objective,
        A_ub=capacity_matrix,
        b_ub=instance.facility_kw * instance.slot_hours,
        A_eq=energy_matrix,
        b_eq=np.array([vehicle.energy_kwh for vehicle in instance.vehicles]),
        bounds=bounds,
        method="highs",
    )
    duration = perf_counter() - started
    if not result.success or result.x is None:
        return ScheduleResult("exact_lp", "INFEASIBLE", None, duration, str(result.message))
    schedule = np.asarray(result.x).reshape(vehicle_count, slot_count)
    schedule[np.abs(schedule) < 1e-10] = 0.0
    check = verify_schedule(instance, schedule)
    status = "OPTIMAL" if check.feasible else "INVALID_SOLUTION"
    return ScheduleResult("exact_lp", status, schedule, duration, str(result.message))


METHODS: dict[str, Callable[[ChargingInstance], ScheduleResult]] = {
    "first_available": first_available_schedule,
    "cheapest_feasible_slot": cheapest_slot_schedule,
    "exact_lp": exact_lp_schedule,
}


def brute_force_grid_objective(instance: ChargingInstance, step_kwh: float = 1.0) -> float:
    """Independent tiny-instance oracle; intended only for tests, not study scaling."""
    if step_kwh <= 0:
        raise ValueError("step must be positive")
    allowed = [
        (vehicle_index, slot)
        for vehicle_index, vehicle in enumerate(instance.vehicles)
        for slot in range(vehicle.arrival_slot, vehicle.departure_slot)
    ]
    maxima = [instance.vehicles[vehicle_index].max_kw * instance.slot_hours for vehicle_index, _ in allowed]
    grids = [np.arange(0.0, maximum + step_kwh / 2, step_kwh) for maximum in maxima]
    best = float("inf")
    for values in itertools.product(*grids):
        schedule = np.zeros((len(instance.vehicles), instance.slot_count))
        for (vehicle_index, slot), value in zip(allowed, values, strict=True):
            schedule[vehicle_index, slot] = value
        if verify_schedule(instance, schedule).feasible:
            best = min(best, schedule_cost(instance, schedule))
    if not np.isfinite(best):
        raise ValueError("grid oracle found no feasible schedule")
    return best


def tiny_oracle_instance() -> ChargingInstance:
    return ChargingInstance(
        name="tiny_oracle",
        prices_per_kwh=np.array([3.0, 1.0, 2.0]),
        facility_kw=np.ones(3),
        vehicles=(Vehicle("A", 0, 2, 1.0, 1.0), Vehicle("B", 1, 3, 1.0, 1.0)),
    )


def _result_metrics(instance: ChargingInstance, result: ScheduleResult) -> dict[str, Any]:
    if result.schedule_kwh is None:
        return {
            "feasible": False,
            "cost": None,
            "unmet_energy_kwh": None,
            "peak_kw": None,
            "peak_utilization": None,
            "max_constraint_violation_kwh": None,
        }
    check = verify_schedule(instance, result.schedule_kwh)
    return {
        "feasible": check.feasible,
        "cost": schedule_cost(instance, result.schedule_kwh),
        "unmet_energy_kwh": check.unmet_energy_kwh,
        "peak_kw": check.peak_kw,
        "peak_utilization": check.peak_utilization,
        "max_constraint_violation_kwh": max(
            check.max_capacity_violation_kwh,
            check.max_vehicle_rate_violation_kwh,
            check.max_window_violation_kwh,
        ),
    }


def _benchmark(
    instance: ChargingInstance,
    repeats: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, ScheduleResult]]:
    raw_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    representative: dict[str, ScheduleResult] = {}
    for method_name, method in METHODS.items():
        results = [method(instance) for _ in range(repeats)]
        median_runtime = float(np.median([result.runtime_seconds for result in results]))
        measured = min(results, key=lambda item: abs(item.runtime_seconds - median_runtime))
        selected = replace(measured, runtime_seconds=median_runtime)
        representative[method_name] = selected
        for repeat_index, result in enumerate(results):
            raw_rows.append(
                {
                    "scenario": instance.name,
                    "method": method_name,
                    "repeat": repeat_index,
                    "runtime_seconds": result.runtime_seconds,
                    "status": result.status,
                }
            )
        metrics = _result_metrics(instance, selected)
        summary_rows.append(
            {
                "scenario": instance.name,
                "fleet_size": len(instance.vehicles),
                "method": method_name,
                "status": selected.status,
                **metrics,
                "median_runtime_seconds": median_runtime,
            }
        )
    return raw_rows, summary_rows, representative


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("cannot write an empty CSV")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def run_experiment(profile: str = "quick", output_dir: Path | None = None) -> ExperimentResult:
    if profile not in {"quick", "full"}:
        raise ValueError("profile must be quick or full")
    started = perf_counter()
    output_dir = output_dir or Path("results/e")
    output_dir.mkdir(parents=True, exist_ok=True)
    repeats = 5 if profile == "quick" else 20

    feasible = make_feasible_instance()
    infeasible = make_infeasible_instance()
    benchmark_raw: list[dict[str, Any]] = []
    comparison_rows: list[dict[str, Any]] = []
    schedules: list[dict[str, Any]] = []
    representatives: dict[str, dict[str, ScheduleResult]] = {}
    for instance in (feasible, infeasible):
        raw, summaries, selected = _benchmark(instance, repeats)
        benchmark_raw.extend(raw)
        comparison_rows.extend(summaries)
        representatives[instance.name] = selected
        for method_name, result in selected.items():
            if result.schedule_kwh is None:
                continue
            for vehicle, row in zip(instance.vehicles, result.schedule_kwh, strict=True):
                for slot, energy in enumerate(row):
                    schedules.append(
                        {
                            "scenario": instance.name,
                            "method": method_name,
                            "vehicle_id": vehicle.vehicle_id,
                            "slot": slot,
                            "energy_kwh": energy,
                        }
                    )

    scaling_rows: list[dict[str, Any]] = []
    for size in ((4, 8, 16, 24) if profile == "quick" else (4, 8, 16, 24, 32, 48, 64)):
        instance = make_fleet_instance(size)
        _, summaries, _ = _benchmark(instance, 3 if profile == "quick" else 10)
        scaling_rows.extend(summaries)

    sensitivity_rows: list[dict[str, Any]] = []
    for factor in (0.5, 0.75, 1.0, 1.25):
        instance = replace(
            feasible,
            name=f"capacity_{factor:.2f}",
            facility_kw=feasible.facility_kw * factor,
        )
        _, summaries, _ = _benchmark(instance, 3 if profile == "quick" else 10)
        for row in summaries:
            sensitivity_rows.append({"capacity_factor": factor, **row})

    tiny = tiny_oracle_instance()
    tiny_lp = exact_lp_schedule(tiny)
    if tiny_lp.schedule_kwh is None:
        raise RuntimeError("tiny LP oracle instance unexpectedly infeasible")
    grid_objective = brute_force_grid_objective(tiny)
    lp_objective = schedule_cost(tiny, tiny_lp.schedule_kwh)
    oracle_error = abs(grid_objective - lp_objective)
    if oracle_error > TOLERANCE:
        raise RuntimeError("LP objective disagrees with independent grid oracle")

    vehicle_rows = [
        {
            "scenario": instance.name,
            "vehicle_id": vehicle.vehicle_id,
            "arrival_slot": vehicle.arrival_slot,
            "departure_slot": vehicle.departure_slot,
            "energy_kwh": vehicle.energy_kwh,
            "max_kw": vehicle.max_kw,
        }
        for instance in (feasible, infeasible)
        for vehicle in instance.vehicles
    ]
    slot_rows = [
        {
            "scenario": instance.name,
            "slot": slot,
            "price_per_kwh": instance.prices_per_kwh[slot],
            "facility_kw": instance.facility_kw[slot],
        }
        for instance in (feasible, infeasible)
        for slot in range(instance.slot_count)
    ]
    feasible_rows = [row for row in comparison_rows if row["scenario"] == feasible.name]
    baseline = next(row for row in feasible_rows if row["method"] == "first_available")
    exact = next(row for row in feasible_rows if row["method"] == "exact_lp")
    heuristic = next(row for row in feasible_rows if row["method"] == "cheapest_feasible_slot")
    if not all(bool(row["feasible"]) for row in feasible_rows):
        raise RuntimeError("fixed feasible study did not produce feasible schedules")
    if exact["cost"] is None or baseline["cost"] is None or heuristic["cost"] is None:
        raise RuntimeError("fixed feasible study is missing a measured objective")

    _write_csv(output_dir / "vehicles.csv", vehicle_rows)
    _write_csv(output_dir / "slots.csv", slot_rows)
    _write_csv(output_dir / "benchmark_raw.csv", benchmark_raw)
    _write_csv(output_dir / "comparison.csv", comparison_rows)
    _write_csv(output_dir / "schedules.csv", schedules)
    _write_csv(output_dir / "fleet_scaling.csv", scaling_rows)
    _write_csv(output_dir / "capacity_sensitivity.csv", sensitivity_rows)
    write_bar_svg(
        ["first available", "cheapest slot", "exact LP"],
        [float(baseline["cost"]), float(heuristic["cost"]), float(exact["cost"])],
        output_dir / "cost_comparison.svg",
        "Track E electricity cost on fixed feasible case",
    )
    runtime_by_size = [row for row in scaling_rows if row["method"] == "exact_lp"]
    write_bar_svg(
        [str(row["fleet_size"]) for row in runtime_by_size],
        [float(row["median_runtime_seconds"]) for row in runtime_by_size],
        output_dir / "lp_scaling.svg",
        "Track E exact LP median runtime by fleet size",
    )

    infeasible_exact = representatives[infeasible.name]["exact_lp"]
    summary = {
        "profile": profile,
        "seed": SEED,
        "environment": environment_metadata(),
        "model": {
            "decision_variable": "x[v,t] = continuous kWh delivered to vehicle v during one slot",
            "objective": "minimize sum_t price[t] * sum_v x[v,t]",
            "constraints": [
                "x[v,t] is zero outside the vehicle arrival/departure window",
                "0 <= x[v,t] <= vehicle max kW * slot hours",
                "sum_v x[v,t] <= facility kW[t] * slot hours",
                "sum_t x[v,t] = required vehicle energy",
            ],
        },
        "fixed_feasible": {
            "baseline_cost": baseline["cost"],
            "cheapest_slot_cost": heuristic["cost"],
            "exact_lp_cost": exact["cost"],
            "exact_saving_vs_baseline": float(baseline["cost"]) - float(exact["cost"]),
            "baseline_peak_utilization": baseline["peak_utilization"],
            "exact_peak_utilization": exact["peak_utilization"],
        },
        "infeasible_case": {
            "exact_lp_status": infeasible_exact.status,
            "solver_message": infeasible_exact.solver_message,
            "cause": "EV-X requests 7 kWh in one slot with a 3 kW per-vehicle limit",
        },
        "objective_oracle": {
            "instance": tiny.name,
            "grid_step_kwh": 1.0,
            "grid_objective": grid_objective,
            "lp_objective": lp_objective,
            "absolute_error": oracle_error,
        },
        "benchmark_protocol": {
            "quick_repeats": repeats,
            "timed_region": "scheduler/solver call only; instance generation and artifact I/O excluded",
            "comparison": "all methods receive the same immutable instance for each row group",
        },
        "full_profile_status": "DONE" if profile == "full" else "NOT RUN",
        "limitations": [
            "Inputs are deterministic synthetic campus scenarios, not operational charging records.",
            "The greedy method respects local rate/window/capacity limits but can leave demand unmet even when a global feasible schedule exists.",
            "The LP assumes divisible energy, known arrivals/departures and prices, constant within-slot power, and no charger assignment or battery tapering losses.",
            "Peak load is a reported metric rather than an objective, so cost optimization need not improve it.",
            "Sub-millisecond heuristic timings and short LP timings are sensitive to host load; raw repeats are retained.",
        ],
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return ExperimentResult(
        track="e",
        profile=profile,
        status=RunStatus.DONE,
        method="first-available vs cheapest-slot vs exact-lp",
        objective=float(exact["cost"]),
        duration_seconds=perf_counter() - started,
        seed=SEED,
        message=f"wrote measured Track E artifacts to {output_dir}",
        metrics={
            "baseline_cost": baseline["cost"],
            "heuristic_cost": heuristic["cost"],
            "exact_lp_cost": exact["cost"],
            "infeasible_case_detected": infeasible_exact.status == "INFEASIBLE",
            "objective_oracle_error": oracle_error,
        },
        metadata=environment_metadata(),
    )
