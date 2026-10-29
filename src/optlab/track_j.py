from __future__ import annotations

import csv
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from time import perf_counter
from typing import Any, Iterable, Sequence

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

from .experiment import environment_metadata
from .models import ExperimentResult, RunStatus
from .plotting import write_bar_svg

SEED = 2026
BUDGET_FRACTIONS = (0.25, 0.50, 0.75, 1.00)
PROFILE_REPEATS = 3
FAULT_WEIGHT = 5.0
PRE_J_EXCLUSIONS = {"track_j.py", "pytest_profile.py"}


@dataclass(frozen=True)
class Mutation:
    fault_id: str
    description: str
    source_file: str
    original: str
    replacement: str
    test_file: str


MUTATIONS: tuple[Mutation, ...] = (
    Mutation(
        "M_A_GRADIENT_SIGN",
        "flip the ridge regularization-gradient sign",
        "src/optlab/track_a.py",
        "return x.T @ (x @ weights - y) / len(x) + self.regularization * weights",
        "return x.T @ (x @ weights - y) / len(x) - self.regularization * weights",
        "tests/test_track_a.py",
    ),
    Mutation(
        "M_B_MAXCUT_EDGE",
        "count equal rather than cut Max-Cut endpoints",
        "src/optlab/track_b.py",
        'if bits[i] != bits[j]))',
        'if bits[i] == bits[j]))',
        "tests/test_track_b.py",
    ),
    Mutation(
        "M_E_CAPACITY_SIGN",
        "reverse the EV facility-capacity violation sign",
        "src/optlab/track_e.py",
        "np.max(slot_energy - slot_energy_limit, initial=0.0)",
        "np.max(slot_energy_limit - slot_energy, initial=0.0)",
        "tests/test_track_e.py",
    ),
    Mutation(
        "M_F_ADD_AS_SUB",
        "compile addition as subtraction in the shared arithmetic evaluator",
        "src/optlab/track_f.py",
        "return left + right",
        "return left - right",
        "tests/test_track_f.py",
    ),
    Mutation(
        "M_H_BUDGET_COMPARATOR",
        "reverse the greedy index-budget feasibility comparator",
        "src/optlab/track_h.py",
        'if trial["storage_bytes"] > budget_bytes:',
        'if trial["storage_bytes"] < budget_bytes:',
        "tests/test_track_h.py",
    ),
    Mutation(
        "M_I_MODULAR_MULTIPLICATION",
        "replace modular multiplication with modular addition in compiled Shor",
        "src/optlab/track_i.py",
        "transformed = (base * value) % modulus if value < modulus else value",
        "transformed = (base + value) % modulus if value < modulus else value",
        "tests/test_track_i.py",
    ),
)


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def count_maintained_source_loc(source: Path, exclusions: set[str] | None = None) -> tuple[int, list[dict[str, Any]]]:
    excluded = exclusions or set()
    rows = []
    for path in sorted(source.glob("*.py")):
        if path.name in excluded:
            continue
        physical = path.read_text(encoding="utf-8").splitlines()
        maintained = sum(1 for line in physical if line.strip() and not line.lstrip().startswith("#"))
        rows.append({"file": str(path.relative_to(source.parent.parent)), "maintained_source_lines": maintained})
    return sum(row["maintained_source_lines"] for row in rows), rows


def features_for_node(nodeid: str) -> tuple[str, ...]:
    path, test_name = nodeid.split("::", 1)
    component = Path(path).stem.removeprefix("test_")
    behavior = test_name.removeprefix("test_")
    features = {f"component:{component}", f"behavior:{component}:{behavior}"}
    lowered = behavior.lower()
    if "seed" in lowered or "reproduc" in lowered:
        features.add("cross:reproducibility")
    if "oracle" in lowered or "exact" in lowered:
        features.add("cross:independent_oracle")
    if any(word in lowered for word in ("equivalent", "agree", "identical", "match")):
        features.add("cross:semantic_equivalence")
    if "noise" in lowered:
        features.add("cross:noise_robustness")
    if "maxcut" in lowered:
        features.add("shared:maxcut_representation")
    return tuple(sorted(features))


def _subprocess_environment(python_path: Path | None = None) -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        {
            "MPLCONFIGDIR": "/tmp/optlab-matplotlib",
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "PYTHONHASHSEED": str(SEED),
        }
    )
    if python_path is not None:
        existing = environment.get("PYTHONPATH", "")
        environment["PYTHONPATH"] = str(python_path) + (os.pathsep + existing if existing else "")
    return environment


def profile_test_suite(root: Path, output_dir: Path, repeats: int = PROFILE_REPEATS) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[float]]:
    raw_rows = []
    suite_walls = []
    output_dir.mkdir(parents=True, exist_ok=True)
    for repeat in range(repeats):
        json_path = output_dir / f"profile-{repeat}.json"
        command = [
            sys.executable,
            "-m",
            "optlab.pytest_profile",
            str(json_path),
            "-q",
            "-m",
            "not slow and not external",
        ]
        started = perf_counter()
        completed = subprocess.run(
            command,
            cwd=root,
            env=_subprocess_environment(),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        suite_walls.append(perf_counter() - started)
        (output_dir / f"profile-{repeat}.log").write_text(completed.stdout, encoding="utf-8")
        if completed.returncode != 0:
            raise RuntimeError(f"pytest profiling repeat {repeat} failed; see profile-{repeat}.log")
        rows = json.loads(json_path.read_text(encoding="utf-8"))
        for row in rows:
            raw_rows.append({"repeat": repeat, **row})
    nodeids = sorted({row["nodeid"] for row in raw_rows})
    costs = []
    for nodeid in nodeids:
        values = [float(row["total_seconds"]) for row in raw_rows if row["nodeid"] == nodeid]
        costs.append(
            {
                "nodeid": nodeid,
                "median_seconds": max(float(median(values)), 1e-6),
                "minimum_seconds": min(values),
                "maximum_seconds": max(values),
                "profile_repeats": repeats,
            }
        )
    return raw_rows, costs, suite_walls


def _prepare_mutation_copy(root: Path, temporary: Path, mutation: Mutation) -> None:
    shutil.copytree(root / "src" / "optlab", temporary / "src" / "optlab")
    (temporary / "tests").mkdir(parents=True)
    shutil.copy2(root / mutation.test_file, temporary / mutation.test_file)
    shutil.copytree(root / "tracks", temporary / "tracks")
    target = temporary / mutation.source_file
    contents = target.read_text(encoding="utf-8")
    if contents.count(mutation.original) != 1:
        raise RuntimeError(f"mutation {mutation.fault_id} target is not unique")
    target.write_text(contents.replace(mutation.original, mutation.replacement, 1), encoding="utf-8")


def run_mutation_fixture(root: Path, output_dir: Path, mutation: Mutation) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix=f"optlab-{mutation.fault_id.lower()}-") as name:
        temporary = Path(name)
        _prepare_mutation_copy(root, temporary, mutation)
        command = [sys.executable, "-m", "pytest", "-q", mutation.test_file]
        started = perf_counter()
        completed = subprocess.run(
            command,
            cwd=temporary,
            env=_subprocess_environment(temporary / "src"),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        elapsed = perf_counter() - started
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / f"{mutation.fault_id}.log"
    log_path.write_text(completed.stdout, encoding="utf-8")
    failing = sorted(set(re.findall(r"FAILED (tests/[^\s]+::[^\s]+)", completed.stdout)))
    return {
        "fault_id": mutation.fault_id,
        "description": mutation.description,
        "source_file": mutation.source_file,
        "test_scope": mutation.test_file,
        "return_code": completed.returncode,
        "detected": completed.returncode != 0 and bool(failing),
        "failing_tests": failing,
        "failing_test_count": len(failing),
        "wall_seconds": elapsed,
        "log": str(log_path.relative_to(root)),
    }


def build_coverage(
    nodeids: Sequence[str], mutation_rows: Sequence[dict[str, Any]]
) -> tuple[dict[str, set[str]], dict[str, float], list[dict[str, Any]], list[dict[str, Any]]]:
    coverage = {nodeid: set(features_for_node(nodeid)) for nodeid in nodeids}
    weights: dict[str, float] = {feature: 1.0 for values in coverage.values() for feature in values}
    fault_matrix = []
    for mutation in mutation_rows:
        fault = f"fault:{mutation['fault_id']}"
        weights[fault] = FAULT_WEIGHT
        detectors = set(mutation["failing_tests"])
        for nodeid in nodeids:
            detected = nodeid in detectors
            if detected:
                coverage[nodeid].add(fault)
            fault_matrix.append(
                {
                    "nodeid": nodeid,
                    "fault_id": mutation["fault_id"],
                    "detected_in_scoped_run": detected,
                    "mutation_test_scope": mutation["test_scope"],
                }
            )
    feature_matrix = [
        {"nodeid": nodeid, "feature_or_fault": item, "weight": weights[item]}
        for nodeid in nodeids
        for item in sorted(coverage[nodeid])
    ]
    return coverage, weights, feature_matrix, fault_matrix


def selection_objective(selected: Iterable[str], coverage: dict[str, set[str]], weights: dict[str, float]) -> float:
    covered = set().union(*(coverage[nodeid] for nodeid in selected)) if selected else set()
    return float(sum(weights[item] for item in covered))


def alphabetical_selection(nodeids: Sequence[str], costs: dict[str, float], budget: float) -> list[str]:
    selected = []
    elapsed = 0.0
    for nodeid in sorted(nodeids):
        cost = costs[nodeid]
        if elapsed + cost > budget:
            break
        selected.append(nodeid)
        elapsed += cost
    return selected


def greedy_maximum_coverage(
    nodeids: Sequence[str], costs: dict[str, float], coverage: dict[str, set[str]], weights: dict[str, float], budget: float
) -> list[str]:
    selected = []
    covered: set[str] = set()
    remaining = set(nodeids)
    elapsed = 0.0
    while remaining:
        feasible = [nodeid for nodeid in remaining if elapsed + costs[nodeid] <= budget + 1e-12]
        if not feasible:
            break
        ranked = []
        for nodeid in feasible:
            gain = sum(weights[item] for item in coverage[nodeid] - covered)
            ranked.append((gain / costs[nodeid], gain, -costs[nodeid], nodeid))
        _, gain, _, choice = max(ranked)
        if gain <= 0:
            break
        selected.append(choice)
        covered.update(coverage[choice])
        elapsed += costs[choice]
        remaining.remove(choice)
    return selected


def exact_maximum_coverage_ilp(
    nodeids: Sequence[str], costs: dict[str, float], coverage: dict[str, set[str]], weights: dict[str, float], budget: float
) -> list[str]:
    items = sorted(weights)
    item_position = {item: position for position, item in enumerate(items)}
    test_count, item_count = len(nodeids), len(items)
    variable_count = test_count + item_count
    objective = np.zeros(variable_count)
    objective[test_count:] = -np.array([weights[item] for item in items])
    objective[:test_count] = 1e-9 * np.array([costs[nodeid] for nodeid in nodeids])
    rows = []
    upper = []
    for item in items:
        constraint = np.zeros(variable_count)
        constraint[test_count + item_position[item]] = 1.0
        for test_position, nodeid in enumerate(nodeids):
            if item in coverage[nodeid]:
                constraint[test_position] = -1.0
        rows.append(constraint)
        upper.append(0.0)
    budget_row = np.zeros(variable_count)
    budget_row[:test_count] = [costs[nodeid] for nodeid in nodeids]
    rows.append(budget_row)
    upper.append(budget)
    result = milp(
        c=objective,
        integrality=np.ones(variable_count),
        bounds=Bounds(np.zeros(variable_count), np.ones(variable_count)),
        constraints=LinearConstraint(np.vstack(rows), lb=-np.inf, ub=np.asarray(upper)),
        options={"time_limit": 20.0},
    )
    if not result.success or result.x is None:
        raise RuntimeError(f"test-selection ILP failed: {result.message}")
    return [nodeid for position, nodeid in enumerate(nodeids) if result.x[position] > 0.5]


def prioritize_selected(
    selected: Sequence[str], costs: dict[str, float], coverage: dict[str, set[str]], weights: dict[str, float]
) -> list[str]:
    ordered = []
    covered: set[str] = set()
    remaining = set(selected)
    while remaining:
        choice = max(
            remaining,
            key=lambda nodeid: (
                sum(weights[item] for item in coverage[nodeid] - covered) / costs[nodeid],
                -costs[nodeid],
                nodeid,
            ),
        )
        ordered.append(choice)
        covered.update(coverage[choice])
        remaining.remove(choice)
    return ordered


def run_selected_tests(root: Path, selected: Sequence[str], log_path: Path) -> dict[str, Any]:
    if not selected:
        raise ValueError("selected test list cannot be empty")
    command = [sys.executable, "-m", "pytest", "-q", *selected]
    started = perf_counter()
    completed = subprocess.run(
        command,
        cwd=root,
        env=_subprocess_environment(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    elapsed = perf_counter() - started
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(completed.stdout, encoding="utf-8")
    return {
        "actual_wall_seconds": elapsed,
        "return_code": completed.returncode,
        "passed": completed.returncode == 0,
        "log": str(log_path.relative_to(root)),
    }


def early_detection_rows(
    method: str,
    fraction: float,
    ordered: Sequence[str],
    costs: dict[str, float],
    mutation_rows: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for mutation in mutation_rows:
        detectors = set(mutation["failing_tests"])
        position = next((index for index, nodeid in enumerate(ordered) if nodeid in detectors), None)
        detection_seconds = None if position is None else sum(costs[nodeid] for nodeid in ordered[: position + 1])
        rows.append(
            {
                "budget_fraction": fraction,
                "method": method,
                "fault_id": mutation["fault_id"],
                "detected": position is not None,
                "first_detection_position": "" if position is None else position + 1,
                "predicted_seconds_to_detection": "" if detection_seconds is None else detection_seconds,
            }
        )
    return rows


def _write_csv(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def run_experiment(profile: str = "quick", output_dir: Path | None = None) -> ExperimentResult:
    if profile not in {"quick", "full"}:
        raise ValueError("profile must be quick or full")
    if profile == "full":
        return ExperimentResult(
            track="j",
            profile="full",
            status=RunStatus.NOT_RUN,
            message="full mutation/scaling profile was not run; quick already executes the real fast suite",
        )
    total_started = perf_counter()
    root = repository_root()
    output_dir = output_dir or root / "results" / "j"
    output_dir.mkdir(parents=True, exist_ok=True)

    source_loc, source_rows = count_maintained_source_loc(root / "src" / "optlab", PRE_J_EXCLUSIONS)
    if source_loc < 1_000:
        raise RuntimeError(f"Track J requires at least 1,000 maintained source LOC; observed {source_loc}")

    profile_raw, cost_rows, suite_walls = profile_test_suite(root, output_dir / "profile_logs")
    nodeids = [row["nodeid"] for row in cost_rows]
    costs = {row["nodeid"]: float(row["median_seconds"]) for row in cost_rows}
    mutation_rows = [run_mutation_fixture(root, output_dir / "mutation_logs", mutation) for mutation in MUTATIONS]
    if not all(row["detected"] for row in mutation_rows):
        survivors = [row["fault_id"] for row in mutation_rows if not row["detected"]]
        raise RuntimeError(f"injected mutation fixtures survived their scoped tests: {survivors}")

    coverage, weights, feature_matrix, fault_matrix = build_coverage(nodeids, mutation_rows)
    total_predicted = sum(costs.values())
    selection_rows = []
    selected_test_rows = []
    execution_rows = []
    early_rows = []
    for fraction in BUDGET_FRACTIONS:
        budget = total_predicted * fraction
        method_functions = (
            ("alphabetical_prefix", lambda: alphabetical_selection(nodeids, costs, budget)),
            ("greedy_weighted_maximum_coverage", lambda: greedy_maximum_coverage(nodeids, costs, coverage, weights, budget)),
            ("exact_maximum_coverage_ilp", lambda: exact_maximum_coverage_ilp(nodeids, costs, coverage, weights, budget)),
        )
        for method, select in method_functions:
            selection_started = perf_counter()
            selected = select()
            selection_seconds = perf_counter() - selection_started
            if method == "exact_maximum_coverage_ilp":
                selected = prioritize_selected(selected, costs, coverage, weights)
            predicted = sum(costs[nodeid] for nodeid in selected)
            if predicted > budget + 1e-9:
                raise RuntimeError(f"{method} exceeded its predicted budget")
            selected_items = set().union(*(coverage[nodeid] for nodeid in selected)) if selected else set()
            detected_faults = {item for item in selected_items if item.startswith("fault:")}
            log_name = f"{int(fraction * 100):03d}-{method}.log"
            execution = run_selected_tests(root, selected, output_dir / "execution_logs" / log_name)
            selection_rows.append(
                {
                    "budget_fraction": fraction,
                    "budget_seconds": budget,
                    "method": method,
                    "selected_tests": len(selected),
                    "predicted_test_seconds": predicted,
                    "budget_feasible": predicted <= budget + 1e-9,
                    "weighted_coverage_objective": selection_objective(selected, coverage, weights),
                    "covered_items": len(selected_items),
                    "detected_injected_faults": len(detected_faults),
                    "undetected_injected_faults": len(MUTATIONS) - len(detected_faults),
                    "selection_overhead_seconds": selection_seconds,
                    **execution,
                }
            )
            cumulative = 0.0
            for order, nodeid in enumerate(selected, start=1):
                cumulative += costs[nodeid]
                selected_test_rows.append(
                    {
                        "budget_fraction": fraction,
                        "method": method,
                        "order": order,
                        "nodeid": nodeid,
                        "median_profiled_seconds": costs[nodeid],
                        "cumulative_profiled_seconds": cumulative,
                    }
                )
            early_rows.extend(early_detection_rows(method, fraction, selected, costs, mutation_rows))

    _write_csv(output_dir / "source_loc.csv", source_rows)
    _write_csv(output_dir / "test_profile_raw.csv", profile_raw)
    _write_csv(output_dir / "test_costs.csv", cost_rows)
    _write_csv(output_dir / "feature_matrix.csv", feature_matrix)
    _write_csv(output_dir / "fault_detection_matrix.csv", fault_matrix)
    serializable_mutations = [
        {**row, "failing_tests": ";".join(row["failing_tests"])} for row in mutation_rows
    ]
    _write_csv(output_dir / "mutations.csv", serializable_mutations)
    _write_csv(output_dir / "selection_comparison.csv", selection_rows)
    _write_csv(output_dir / "selected_tests.csv", selected_test_rows)
    _write_csv(output_dir / "early_detection.csv", early_rows)

    summary = {
        "profile": "quick",
        "date": "2026-10-29",
        "seed": SEED,
        "environment": environment_metadata(),
        "source_loc_before_track_j": source_loc,
        "source_file_count_before_track_j": len(source_rows),
        "source_loc_policy": "nonblank, non-comment physical Python lines in src/optlab; tests/vendor/generated and Track J additions excluded",
        "profiled_test_count": len(nodeids),
        "profile_repeats": PROFILE_REPEATS,
        "median_full_suite_subprocess_wall_seconds": float(median(suite_walls)),
        "summed_median_test_phase_seconds": total_predicted,
        "injected_mutations": len(MUTATIONS),
        "all_mutations_detected_in_scoped_runs": all(row["detected"] for row in mutation_rows),
        "budgets": list(BUDGET_FRACTIONS),
        "objective": "maximize weighted covered test behaviors and observed injected-fault detections under measured test-phase budget",
        "variables": "binary x_t selects test t; exact ILP also uses binary y_k for covered feature/fault k",
        "constraints": "sum_t measured_cost_t x_t <= budget; y_k <= sum_{t covers k} x_t",
        "fault_weight": FAULT_WEIGHT,
        "selection_results": selection_rows,
        "full_profile_status": "NOT RUN",
        "limitations": [
            "Injected mutations are labeled synthetic faults, not observed production defects.",
            "Mutation detection is conservatively grounded in each affected track's scoped test-file run; unrun cross-track detectors are not credited.",
            "Per-test phase costs exclude fixed pytest collection/import startup, while actual selected-suite wall times include it.",
            "Three timing repeats on one WSL2 host remain sensitive to load and simulator initialization.",
            "Feature coverage is grounded in test node/component names and assertions, not line-coverage instrumentation.",
            "Normal CI remains the complete fast suite; selection is an experiment and does not weaken the workflow.",
        ],
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_bar_svg(
        [f"{int(row['budget_fraction'] * 100)}% {row['method'].split('_')[0]}" for row in selection_rows],
        [float(row["weighted_coverage_objective"]) for row in selection_rows],
        output_dir / "coverage_objective.svg",
        "Track J weighted feature/fault coverage under measured budgets",
    )
    midpoint = [row for row in selection_rows if row["budget_fraction"] == 0.5]
    best = max(midpoint, key=lambda row: row["weighted_coverage_objective"])
    return ExperimentResult(
        track="j",
        profile="quick",
        status=RunStatus.DONE,
        method="real pytest profiling with alphabetical, greedy coverage, and exact maximum-coverage ILP",
        objective=float(best["weighted_coverage_objective"]),
        duration_seconds=perf_counter() - total_started,
        seed=SEED,
        message=f"profiled {len(nodeids)} real tests and {len(MUTATIONS)} isolated injected mutations",
        metrics={
            "source_loc_before_track_j": source_loc,
            "profiled_test_count": len(nodeids),
            "all_mutations_detected": True,
            "midpoint_best_method": best["method"],
            "midpoint_detected_faults": best["detected_injected_faults"],
        },
        metadata=environment_metadata(),
    )
