from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class ValidationRow:
    track: str
    status: str
    checks: int
    detail: str


def _load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _validate_a(data: dict[str, Any]) -> int:
    checks = data["gradient_checks"]
    _require(checks["manual_vs_autograd_max_abs"] < 1e-10, "manual/autograd mismatch")
    _require(checks["manual_vs_finite_difference_max_abs"] < 1e-6, "finite-difference mismatch")
    return 2


def _validate_b(data: dict[str, Any]) -> int:
    _require(data["knapsack"]["exact_methods_match_oracle"], "knapsack exact methods disagree")
    _require(data["maxcut"]["max_abs_qubo_minus_ising_error"] < 1e-10, "QUBO/Ising mismatch")
    _require(data["maxcut"]["max_abs_qubo_plus_cut_error"] < 1e-10, "QUBO/cut mismatch")
    return 3


def _validate_c(data: dict[str, Any]) -> int:
    qaoa = data["qaoa"]
    _require(qaoa["expectation_cut"] <= qaoa["classical_optimum_cut"] + 1e-9, "QAOA exceeds oracle")
    _require(0.0 <= qaoa["optimal_sample_probability"] <= 1.0, "invalid sample probability")
    _require(0.0 <= data["qnn"]["accuracy"] <= 1.0, "invalid QNN accuracy")
    return 3


def _validate_d(data: dict[str, Any]) -> int:
    submodular = data["submodular"]
    _require(submodular["diminishing_returns"]["passed"], "diminishing returns failed")
    _require(submodular["greedy_value"] <= submodular["exact_value"], "greedy exceeds exact oracle")
    _require(data["fedavg"]["same_split_for_all_methods"], "FedAvg comparison split differs")
    static, stealing = data["work_stealing"]["results"]
    _require(static["stolen_tasks"] == 0, "static deque baseline recorded stolen tasks")
    _require(stealing["stolen_tasks"] > 0, "deque work-stealing run recorded no steals")
    _require(
        all(row["every_task_once"] and row["checksum_matches"] for row in (static, stealing)),
        "deque scheduling lost, duplicated, or corrupted work",
    )
    _require(stealing["owner_end"] == "right" and stealing["thief_end"] == "left", "invalid deque ends")
    return 7


def _validate_e(data: dict[str, Any]) -> int:
    fixed = data["fixed_feasible"]
    _require(fixed["exact_lp_cost"] <= fixed["baseline_cost"] + 1e-9, "LP does not improve baseline")
    _require(data["infeasible_case"]["exact_lp_status"] == "INFEASIBLE", "infeasible case accepted")
    _require(data["objective_oracle"]["absolute_error"] < 1e-9, "tiny objective oracle mismatch")
    return 3


def _validate_f(data: dict[str, Any]) -> int:
    semantic = data["semantic_checks"]
    _require(semantic["all_equivalent"], "compiler semantic equivalence failed")
    _require(len(data["passes"]) >= 4, "fewer than four compiler passes")
    _require(semantic["generated_programs"] > 0, "no generated semantic checks")
    return 3


def _validate_g(data: dict[str, Any]) -> int:
    verification = data["verification"]
    required = (
        "upstream_baseline_boot_and_usertests",
        "priority_change_boot_and_usertests",
        "accounting_change_boot_and_usertests",
        "benchmark_baseline_pass",
        "benchmark_optimized_pass",
    )
    _require(all(verification[name] for name in required), "xv6 boot, usertests, or benchmark failed")
    return len(required)


def _validate_h(data: dict[str, Any]) -> int:
    _require(data["all_subset_results_equal"], "indexed query results differ")
    _require(data["subset_count"] == 64, "index subset enumeration incomplete")
    budget = data["storage_budget_bytes"]
    _require(data["greedy"]["storage_bytes"] <= budget, "greedy index set exceeds storage budget")
    _require(data["exact_ilp"]["storage_bytes"] <= budget, "exact index set exceeds storage budget")
    return 4


def _validate_i(data: dict[str, Any]) -> int:
    _require(all(data["algorithm_correctness"].values()), "quantum algorithm correctness failed")
    models = data["qml_comparison"]
    _require(any(row["circuit_evaluations"] > 0 for row in models), "no quantum QML model measured")
    _require(any(row["circuit_evaluations"] == 0 for row in models), "no classical QML baseline measured")
    return 3


def _validate_j(data: dict[str, Any]) -> int:
    _require(data["source_loc_before_track_j"] >= 1_000, "pre-J codebase is below 1,000 source LOC")
    _require(data["profiled_test_count"] > 0, "no real pytest tests profiled")
    _require(data["all_mutations_detected_in_scoped_runs"], "an injected mutation escaped its scoped tests")
    selections = data["selection_results"]
    _require(all(row["budget_feasible"] and row["passed"] for row in selections), "selected suite failed")
    return 4


VALIDATORS: dict[str, Callable[[dict[str, Any]], int]] = {
    "a": _validate_a,
    "b": _validate_b,
    "c": _validate_c,
    "d": _validate_d,
    "e": _validate_e,
    "f": _validate_f,
    "g": _validate_g,
    "h": _validate_h,
    "i": _validate_i,
    "j": _validate_j,
}


def validate_artifacts(root: Path) -> list[ValidationRow]:
    results = root / "results"
    rows: list[ValidationRow] = []
    for track, validator in VALIDATORS.items():
        summary_path = results / track / "summary.json"
        try:
            _require(summary_path.is_file(), f"missing {summary_path.relative_to(root)}")
            summary = _load(summary_path)
            _require(summary.get("profile") == "quick", "primary summary is not the quick profile")
            checks = validator(summary)
            if track in "abcdef":
                full_path = results / track / "full" / "summary.json"
                _require(full_path.is_file(), f"missing {full_path.relative_to(root)}")
                full = _load(full_path)
                _require(full.get("profile") == "full", "full summary has wrong profile")
                _require(full.get("full_profile_status") == "DONE", "full profile is not DONE")
                checks += 2
            else:
                deferred = summary.get("full_profile_status", summary.get("verification", {}).get("full_profile_status"))
                _require(deferred == "NOT RUN", "deferred full profile status is not explicit")
                checks += 1
            rows.append(ValidationRow(track.upper(), "PASS", checks, "artifact invariants satisfied"))
        except (AssertionError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            rows.append(ValidationRow(track.upper(), "FAIL", 0, str(error)))
    return rows


def write_validation(rows: list[ValidationRow], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "PASS" if all(row.status == "PASS" for row in rows) else "FAIL",
        "tracks": [asdict(row) for row in rows],
    }
    (output_dir / "artifact_validation.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output_dir / "artifact_validation.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("track", "status", "checks", "detail"),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate measured artifacts for Tracks A-J")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, default=Path("results"))
    args = parser.parse_args()
    rows = validate_artifacts(args.root.resolve())
    write_validation(rows, args.output_dir)
    for row in rows:
        print(f"{row.track}: {row.status} ({row.checks} checks) - {row.detail}")
    return 0 if all(row.status == "PASS" for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
