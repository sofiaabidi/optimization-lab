from __future__ import annotations

import csv
import hashlib
import itertools
import json
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from time import perf_counter
from typing import Any, Iterable, Sequence

from .experiment import environment_metadata
from .models import ExperimentResult, RunStatus
from .plotting import write_bar_svg

SEED = 2026
QUICK_STUDENTS = 10_000
ENROLLMENTS_PER_STUDENT = 6
QUICK_REPEATS = 5
STORAGE_BUDGET_BYTES = 2_500_000
TERMS = ("2024F", "2025S", "2025F", "2026S")

SCHEMA_SQL = """
CREATE TABLE departments (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);
CREATE TABLE students (
    id INTEGER PRIMARY KEY,
    department_id INTEGER NOT NULL REFERENCES departments(id),
    advisor_id INTEGER NOT NULL,
    campus TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active', 'leave', 'graduated')),
    entry_year INTEGER NOT NULL,
    last_name TEXT NOT NULL
);
CREATE TABLE courses (
    id INTEGER PRIMARY KEY,
    department_id INTEGER NOT NULL REFERENCES departments(id),
    code TEXT NOT NULL UNIQUE,
    credits INTEGER NOT NULL
);
CREATE TABLE enrollments (
    id INTEGER PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id),
    course_id INTEGER NOT NULL REFERENCES courses(id),
    term TEXT NOT NULL,
    grade REAL NOT NULL,
    completed INTEGER NOT NULL,
    enrolled_at TEXT NOT NULL
);
""".strip()


@dataclass(frozen=True)
class CandidateIndex:
    name: str
    table: str
    columns: tuple[str, ...]

    @property
    def sql(self) -> str:
        return f"CREATE INDEX {self.name} ON {self.table} ({', '.join(self.columns)})"


@dataclass(frozen=True)
class QuerySpec:
    name: str
    weight: int
    sql: str
    parameters: tuple[tuple[Any, ...], ...]


CANDIDATE_INDEXES: tuple[CandidateIndex, ...] = (
    CandidateIndex("idx_enrollment_student_term", "enrollments", ("student_id", "term", "course_id", "grade")),
    CandidateIndex("idx_enrollment_course_term", "enrollments", ("course_id", "term", "student_id", "grade")),
    CandidateIndex("idx_student_advisor_status", "students", ("advisor_id", "status", "last_name")),
    CandidateIndex("idx_course_department", "courses", ("department_id", "code")),
    CandidateIndex("idx_enrollment_risk", "enrollments", ("term", "grade", "student_id")),
    CandidateIndex("idx_student_campus", "students", ("campus", "id")),
)


def workload(student_count: int = QUICK_STUDENTS) -> tuple[QuerySpec, ...]:
    final_student = min(student_count, 9_997)
    return (
        QuerySpec(
            "student_history",
            30,
            """SELECT e.term, c.code, e.grade
                   FROM enrollments AS e JOIN courses AS c ON c.id = e.course_id
                  WHERE e.student_id = ? AND e.term = ?
                  ORDER BY c.code""",
            ((17, "2025F"), (2048 if student_count >= 2048 else student_count, "2026S"), (final_student, "2025S")),
        ),
        QuerySpec(
            "course_roster",
            25,
            """SELECT s.id, s.last_name, e.grade
                   FROM enrollments AS e JOIN students AS s ON s.id = e.student_id
                  WHERE e.course_id = ? AND e.term = ?
                  ORDER BY s.last_name""",
            ((11, "2025F"), (97, "2026S"), (211, "2025S")),
        ),
        QuerySpec(
            "advisor_active_students",
            20,
            """SELECT id, last_name, campus
                   FROM students
                  WHERE advisor_id = ? AND status = ?
                  ORDER BY last_name""",
            ((7, "active"), (51, "active"), (103, "active")),
        ),
        QuerySpec(
            "department_term_gpa",
            15,
            """SELECT c.code, COUNT(*), ROUND(AVG(e.grade), 3)
                   FROM courses AS c JOIN enrollments AS e ON e.course_id = c.id
                  WHERE c.department_id = ? AND e.term = ?
                  GROUP BY c.id, c.code
                  ORDER BY c.code""",
            ((2, "2025F"), (7, "2026S"), (11, "2025S")),
        ),
        QuerySpec(
            "campus_at_risk",
            10,
            """SELECT s.campus, COUNT(*), ROUND(AVG(e.grade), 3)
                   FROM enrollments AS e JOIN students AS s ON s.id = e.student_id
                  WHERE e.term = ? AND e.grade < ? AND s.campus = ?
                  GROUP BY s.campus""",
            (("2025F", 2.0, "north"), ("2026S", 2.2, "central"), ("2025S", 1.8, "south")),
        ),
    )


def _configure(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA journal_mode=DELETE")
    connection.execute("PRAGMA synchronous=OFF")
    connection.execute("PRAGMA temp_store=MEMORY")
    connection.execute("PRAGMA cache_size=-20000")
    connection.execute("PRAGMA automatic_index=ON")


def create_database(path: Path, student_count: int = QUICK_STUDENTS, seed: int = SEED) -> dict[str, int]:
    if student_count < 220:
        raise ValueError("student_count must be at least 220 for the fixed workload")
    if path.exists():
        raise FileExistsError(path)
    connection = sqlite3.connect(path)
    try:
        _configure(connection)
        connection.executescript(SCHEMA_SQL)
        department_rows = [(identifier, f"Department {identifier:02d}") for identifier in range(1, 13)]
        course_rows = [
            (identifier, ((identifier * 5 + seed) % 12) + 1, f"C{identifier:03d}", 3 + (identifier % 2))
            for identifier in range(1, 241)
        ]
        campus_names = ("north", "central", "south")
        statuses = ("active", "active", "active", "active", "active", "leave", "graduated")
        student_rows = [
            (
                identifier,
                ((identifier * 7 + seed) % 12) + 1,
                ((identifier * 17 + seed) % 120) + 1,
                campus_names[(identifier * 11 + seed) % len(campus_names)],
                statuses[(identifier * 13 + seed) % len(statuses)],
                2021 + (identifier % 5),
                f"Student{(identifier * 7919 + seed) % student_count:05d}",
            )
            for identifier in range(1, student_count + 1)
        ]
        enrollment_rows = []
        enrollment_id = 1
        for student_id in range(1, student_count + 1):
            for slot in range(ENROLLMENTS_PER_STUDENT):
                course_id = ((student_id * 13 + slot * 37 + seed) % 240) + 1
                term = TERMS[(student_id + slot * 3 + seed) % len(TERMS)]
                grade = round(1.2 + ((student_id * 37 + slot * 19 + seed) % 29) / 10.0, 1)
                enrollment_rows.append(
                    (
                        enrollment_id,
                        student_id,
                        course_id,
                        term,
                        grade,
                        int(term != "2026S"),
                        f"{term[:4]}-{1 + ((student_id + slot) % 9):02d}-{1 + (student_id % 27):02d}",
                    )
                )
                enrollment_id += 1
        with connection:
            connection.executemany("INSERT INTO departments VALUES (?, ?)", department_rows)
            connection.executemany("INSERT INTO courses VALUES (?, ?, ?, ?)", course_rows)
            connection.executemany("INSERT INTO students VALUES (?, ?, ?, ?, ?, ?, ?)", student_rows)
            connection.executemany("INSERT INTO enrollments VALUES (?, ?, ?, ?, ?, ?, ?)", enrollment_rows)
        connection.execute("ANALYZE")
        connection.commit()
        return {
            "departments": len(department_rows),
            "courses": len(course_rows),
            "students": len(student_rows),
            "enrollments": len(enrollment_rows),
        }
    finally:
        connection.close()


def _database_bytes(connection: sqlite3.Connection) -> int:
    page_count = int(connection.execute("PRAGMA page_count").fetchone()[0])
    page_size = int(connection.execute("PRAGMA page_size").fetchone()[0])
    return page_count * page_size


def _subset_name(index_names: Iterable[str]) -> str:
    names = sorted(index_names)
    return "+".join(names) if names else "none"


def _query_checksum(connection: sqlite3.Connection, spec: QuerySpec) -> str:
    digest = hashlib.sha256()
    for case, parameters in enumerate(spec.parameters):
        rows = connection.execute(spec.sql, parameters).fetchall()
        digest.update(repr((case, parameters, rows)).encode("utf-8"))
    return digest.hexdigest()


def measure_database(
    path: Path,
    selected: Sequence[CandidateIndex],
    specs: Sequence[QuerySpec],
    baseline_bytes: int,
    repeats: int,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    if repeats < 1:
        raise ValueError("repeats must be positive")
    connection = sqlite3.connect(path)
    try:
        _configure(connection)
        started = perf_counter()
        if selected:
            with connection:
                for index in selected:
                    connection.execute(index.sql)
            connection.execute("ANALYZE")
            connection.commit()
        build_seconds = perf_counter() - started if selected else 0.0
        storage_bytes = _database_bytes(connection) - baseline_bytes
        names = tuple(sorted(index.name for index in selected))
        subset = _subset_name(names)
        checksums = {spec.name: _query_checksum(connection, spec) for spec in specs}

        plans: dict[str, list[dict[str, Any]]] = {}
        for spec in specs:
            case_plans = []
            for case, parameters in enumerate(spec.parameters):
                rows = connection.execute("EXPLAIN QUERY PLAN " + spec.sql, parameters).fetchall()
                case_plans.append({"case": case, "parameters": list(parameters), "steps": [row[3] for row in rows]})
                connection.execute(spec.sql, parameters).fetchall()
            plans[spec.name] = case_plans

        raw_rows: list[dict[str, Any]] = []
        medians: dict[str, float] = {}
        for spec in specs:
            timings = []
            for repeat in range(repeats):
                for case, parameters in enumerate(spec.parameters):
                    query_started = perf_counter()
                    rows = connection.execute(spec.sql, parameters).fetchall()
                    elapsed = perf_counter() - query_started
                    timings.append(elapsed)
                    raw_rows.append(
                        {
                            "subset": subset,
                            "query": spec.name,
                            "weight": spec.weight,
                            "case": case,
                            "repeat": repeat,
                            "latency_seconds": elapsed,
                            "row_count": len(rows),
                            "checksum": checksums[spec.name],
                        }
                    )
            medians[spec.name] = float(median(timings))
        objective = sum(spec.weight * medians[spec.name] for spec in specs)
        total_weight = sum(spec.weight for spec in specs)
        measurement = {
            "subset": subset,
            "indexes": names,
            "index_count": len(names),
            "storage_bytes": storage_bytes,
            "build_seconds": build_seconds,
            "weighted_latency_seconds": objective,
            "latency_derived_weighted_queries_per_second": total_weight / objective,
            "checksums": checksums,
            "query_median_seconds": medians,
        }
        return measurement, raw_rows, plans
    finally:
        connection.close()


def benchmark_subsets(
    baseline_path: Path,
    working_directory: Path,
    candidates: Sequence[CandidateIndex],
    specs: Sequence[QuerySpec],
    repeats: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    with sqlite3.connect(baseline_path) as baseline_connection:
        baseline_bytes = _database_bytes(baseline_connection)
    measurements = []
    latency_rows: list[dict[str, Any]] = []
    all_plans: dict[str, Any] = {}
    expected_checksums: dict[str, str] | None = None
    for mask in range(1 << len(candidates)):
        selected = [candidate for bit, candidate in enumerate(candidates) if mask & (1 << bit)]
        copy_path = working_directory / f"subset-{mask:02d}.sqlite"
        shutil.copy2(baseline_path, copy_path)
        try:
            measurement, raw, plans = measure_database(
                copy_path, selected, specs, baseline_bytes=baseline_bytes, repeats=repeats
            )
        finally:
            copy_path.unlink(missing_ok=True)
        if expected_checksums is None:
            expected_checksums = measurement["checksums"]
        if measurement["checksums"] != expected_checksums:
            raise RuntimeError(f"query result mismatch for {measurement['subset']}")
        measurements.append(measurement)
        latency_rows.extend(raw)
        all_plans[measurement["subset"]] = plans
    return measurements, latency_rows, all_plans


def measure_actual_throughput(
    baseline_path: Path,
    copy_path: Path,
    selected: Sequence[CandidateIndex],
    specs: Sequence[QuerySpec],
    cycles: int = 3,
) -> tuple[float, list[dict[str, Any]]]:
    """Measure a single-client weighted stream after index build and warmup."""
    if cycles < 1:
        raise ValueError("cycles must be positive")
    shutil.copy2(baseline_path, copy_path)
    connection = sqlite3.connect(copy_path)
    try:
        _configure(connection)
        if selected:
            with connection:
                for index in selected:
                    connection.execute(index.sql)
            connection.execute("ANALYZE")
            connection.commit()
        for spec in specs:
            for parameters in spec.parameters:
                connection.execute(spec.sql, parameters).fetchall()
        query_count = sum(spec.weight for spec in specs)
        rows = []
        rates = []
        for cycle in range(cycles):
            started = perf_counter()
            executed = 0
            for spec in specs:
                for occurrence in range(spec.weight):
                    parameters = spec.parameters[(cycle + occurrence) % len(spec.parameters)]
                    connection.execute(spec.sql, parameters).fetchall()
                    executed += 1
            elapsed = perf_counter() - started
            rate = executed / elapsed
            rates.append(rate)
            rows.append(
                {
                    "subset": _subset_name(index.name for index in selected),
                    "cycle": cycle,
                    "query_count": executed,
                    "elapsed_seconds": elapsed,
                    "queries_per_second": rate,
                }
            )
        if any(row["query_count"] != query_count for row in rows):
            raise RuntimeError("throughput workload did not execute its declared query count")
        return float(median(rates)), rows
    finally:
        connection.close()
        copy_path.unlink(missing_ok=True)


def greedy_select(measurements: Sequence[dict[str, Any]], budget_bytes: int) -> dict[str, Any]:
    by_names = {frozenset(row["indexes"]): row for row in measurements}
    current = by_names[frozenset()]
    candidates = sorted(set().union(*(set(row["indexes"]) for row in measurements)))
    while True:
        choices = []
        current_names = frozenset(current["indexes"])
        for candidate in candidates:
            if candidate in current_names:
                continue
            trial = by_names[current_names | {candidate}]
            if trial["storage_bytes"] > budget_bytes:
                continue
            benefit = current["weighted_latency_seconds"] - trial["weighted_latency_seconds"]
            incremental_bytes = max(1, trial["storage_bytes"] - current["storage_bytes"])
            if benefit > 0:
                choices.append((benefit / incremental_bytes, benefit, -trial["weighted_latency_seconds"], candidate, trial))
        if not choices:
            return current
        current = max(choices, key=lambda choice: choice[:4])[-1]


def exact_subset_ilp(measurements: Sequence[dict[str, Any]], budget_bytes: int) -> dict[str, Any]:
    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp

    objectives = np.array([row["weighted_latency_seconds"] for row in measurements], dtype=float)
    costs = np.array([row["storage_bytes"] for row in measurements], dtype=float)
    constraints = LinearConstraint(
        np.vstack((np.ones(len(measurements)), costs)),
        lb=np.array([1.0, -np.inf]),
        ub=np.array([1.0, float(budget_bytes)]),
    )
    result = milp(
        c=objectives,
        integrality=np.ones(len(measurements)),
        bounds=Bounds(np.zeros(len(measurements)), np.ones(len(measurements))),
        constraints=constraints,
        options={"time_limit": 10.0},
    )
    if not result.success or result.x is None:
        raise RuntimeError(f"subset ILP failed: {result.message}")
    selected_position = int(np.argmax(result.x))
    selected = measurements[selected_position]
    feasible = [row for row in measurements if row["storage_bytes"] <= budget_bytes]
    oracle = min(feasible, key=lambda row: (row["weighted_latency_seconds"], row["subset"]))
    if abs(selected["weighted_latency_seconds"] - oracle["weighted_latency_seconds"]) > 1e-12:
        raise RuntimeError("ILP objective disagrees with exhaustive feasible-subset oracle")
    return selected


def interaction_rows(measurements: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    by_names = {frozenset(row["indexes"]): row for row in measurements}
    baseline = by_names[frozenset()]["weighted_latency_seconds"]
    names = sorted(set().union(*(set(row["indexes"]) for row in measurements)))
    rows = []
    for first, second in itertools.combinations(names, 2):
        first_benefit = baseline - by_names[frozenset({first})]["weighted_latency_seconds"]
        second_benefit = baseline - by_names[frozenset({second})]["weighted_latency_seconds"]
        pair_benefit = baseline - by_names[frozenset({first, second})]["weighted_latency_seconds"]
        rows.append(
            {
                "first_index": first,
                "second_index": second,
                "first_benefit_seconds": first_benefit,
                "second_benefit_seconds": second_benefit,
                "observed_pair_benefit_seconds": pair_benefit,
                "interaction_seconds": pair_benefit - first_benefit - second_benefit,
            }
        )
    return rows


def _plan_change_count(baseline_plans: dict[str, Any], selected_plans: dict[str, Any]) -> int:
    changes = 0
    for query, cases in baseline_plans.items():
        for baseline_case, selected_case in zip(cases, selected_plans[query], strict=True):
            if baseline_case["steps"] != selected_case["steps"]:
                changes += 1
    return changes


def _write_csv(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty CSV: {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _serializable_measurement(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "subset": row["subset"],
        "indexes": ";".join(row["indexes"]),
        "index_count": row["index_count"],
        "storage_bytes": row["storage_bytes"],
        "build_seconds": row["build_seconds"],
        "weighted_latency_seconds": row["weighted_latency_seconds"],
        "latency_derived_weighted_queries_per_second": row["latency_derived_weighted_queries_per_second"],
    }


def run_experiment(profile: str = "quick", output_dir: Path | None = None) -> ExperimentResult:
    if profile not in {"quick", "full"}:
        raise ValueError("profile must be quick or full")
    if profile == "full":
        return ExperimentResult(
            track="h",
            profile="full",
            status=RunStatus.NOT_RUN,
            message="full SQLite scale profile was not run; use the documented quick experiment",
        )
    started = perf_counter()
    output_dir = output_dir or Path("results/h")
    output_dir.mkdir(parents=True, exist_ok=True)
    specs = workload()
    with tempfile.TemporaryDirectory(prefix="optlab-track-h-") as temporary:
        temporary_path = Path(temporary)
        baseline_path = temporary_path / "baseline.sqlite"
        generation_started = perf_counter()
        row_counts = create_database(baseline_path)
        generation_seconds = perf_counter() - generation_started
        with sqlite3.connect(baseline_path) as connection:
            baseline_bytes = _database_bytes(connection)
            sqlite_version = sqlite3.sqlite_version
        measurements, latency_rows, plans = benchmark_subsets(
            baseline_path,
            temporary_path,
            CANDIDATE_INDEXES,
            specs,
            repeats=QUICK_REPEATS,
        )
        baseline = next(row for row in measurements if not row["indexes"])
        greedy = greedy_select(measurements, STORAGE_BUDGET_BYTES)
        exact = exact_subset_ilp(measurements, STORAGE_BUDGET_BYTES)
        by_name = {candidate.name: candidate for candidate in CANDIDATE_INDEXES}
        actual_throughputs: dict[str, float] = {}
        throughput_rows: list[dict[str, Any]] = []
        method_rows = (("sqlite_default", baseline), ("conditional_greedy", greedy), ("exact_measured_subset_ilp", exact))
        measured_subsets: dict[str, float] = {}
        for method, row in method_rows:
            if row["subset"] in measured_subsets:
                actual_throughputs[method] = measured_subsets[row["subset"]]
                continue
            selected = [by_name[name] for name in row["indexes"]]
            rate, raw_rates = measure_actual_throughput(
                baseline_path,
                temporary_path / f"throughput-{method}.sqlite",
                selected,
                specs,
            )
            actual_throughputs[method] = rate
            measured_subsets[row["subset"]] = rate
            throughput_rows.extend({"method": method, **raw} for raw in raw_rates)

    strategies = []
    for method, row in (("sqlite_default", baseline), ("conditional_greedy", greedy), ("exact_measured_subset_ilp", exact)):
        strategies.append(
            {
                "method": method,
                **_serializable_measurement(row),
                "budget_bytes": STORAGE_BUDGET_BYTES,
                "budget_feasible": row["storage_bytes"] <= STORAGE_BUDGET_BYTES,
                "result_checksums_equal": row["checksums"] == baseline["checksums"],
                "plan_cases_changed": _plan_change_count(plans[baseline["subset"]], plans[row["subset"]]),
                "measured_queries_per_second": actual_throughputs[method],
                "latency_change_vs_baseline": (
                    row["weighted_latency_seconds"] - baseline["weighted_latency_seconds"]
                )
                / baseline["weighted_latency_seconds"],
            }
        )

    query_summary = []
    for method, row in (("sqlite_default", baseline), ("conditional_greedy", greedy), ("exact_measured_subset_ilp", exact)):
        for spec in specs:
            query_summary.append(
                {
                    "method": method,
                    "subset": row["subset"],
                    "query": spec.name,
                    "weight": spec.weight,
                    "median_latency_seconds": row["query_median_seconds"][spec.name],
                    "checksum": row["checksums"][spec.name],
                }
            )

    _write_csv(output_dir / "latency_raw.csv", latency_rows)
    _write_csv(output_dir / "throughput_raw.csv", throughput_rows)
    _write_csv(output_dir / "subset_measurements.csv", [_serializable_measurement(row) for row in measurements])
    _write_csv(output_dir / "strategy_comparison.csv", strategies)
    _write_csv(output_dir / "query_summary.csv", query_summary)
    _write_csv(output_dir / "interactions.csv", interaction_rows(measurements))
    (output_dir / "plans.json").write_text(json.dumps(plans, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "schema.sql").write_text(SCHEMA_SQL + "\n", encoding="utf-8")
    (output_dir / "workload.sql").write_text(
        "\n\n".join(f"-- {spec.name}; weight={spec.weight}\n{spec.sql.strip()};" for spec in specs) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "seed": SEED,
        "row_counts": row_counts,
        "enrollments_per_student": ENROLLMENTS_PER_STUDENT,
        "database_bytes_without_added_indexes": baseline_bytes,
        "sqlite_version": sqlite_version,
        "journal_mode": "DELETE",
        "synchronous": "OFF for reproducible local build/benchmark; no durability claim",
        "automatic_index": True,
        "warmup": "one untimed execution per query parameter case and database copy",
        "timed_repeats_per_case": QUICK_REPEATS,
        "parameter_cases_per_query": 3,
        "throughput_cycles": 3,
        "throughput_queries_per_cycle": sum(spec.weight for spec in specs),
        "storage_budget_bytes": STORAGE_BUDGET_BYTES,
        "candidate_indexes": [
            {"name": index.name, "table": index.table, "columns": list(index.columns), "sql": index.sql}
            for index in CANDIDATE_INDEXES
        ],
    }
    (output_dir / "dataset_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    summary = {
        "profile": "quick",
        "date": "2026-10-29",
        "environment": environment_metadata(),
        "sqlite_version": sqlite_version,
        "dataset_generation_seconds": generation_seconds,
        "subset_count": len(measurements),
        "all_subset_results_equal": all(row["checksums"] == baseline["checksums"] for row in measurements),
        "storage_budget_bytes": STORAGE_BUDGET_BYTES,
        "baseline": _serializable_measurement(baseline),
        "greedy": _serializable_measurement(greedy),
        "exact_ilp": _serializable_measurement(exact),
        "measured_single_client_queries_per_second": actual_throughputs,
        "ilp_formulation": {
            "variables": "binary z_S for each measured candidate-index subset S; x_i is derived from membership",
            "objective": "minimize sum_S measured_weighted_latency(S) * z_S",
            "constraints": ["sum_S z_S = 1", "sum_S measured_storage_bytes(S) * z_S <= budget"],
            "interaction_handling": "each complete subset is measured, so storage and latency interactions are retained",
        },
        "full_profile_status": "NOT RUN",
        "limitations": [
            "The deterministic campus data are synthetic and do not contain production data skew or concurrent writes.",
            "Warm-cache single-client latency on one machine does not predict multi-client production throughput.",
            "The exact one-hot ILP is practical only because six candidates produce 64 measured subsets.",
            "SQLite page allocation is measured per complete subset; it is not assumed additive across indexes.",
            "Timing differences near timer/system-noise scale should not be treated as stable wins without more repeats.",
        ],
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_bar_svg(
        ["default", "greedy", "exact ILP"],
        [row["weighted_latency_seconds"] * 1000 for row in (baseline, greedy, exact)],
        output_dir / "weighted_latency_ms.svg",
        "Track H weighted warm-query latency (ms; lower is better)",
    )
    return ExperimentResult(
        track="h",
        profile="quick",
        status=RunStatus.DONE,
        method="measured SQLite index subsets: conditional greedy and exact ILP",
        objective=exact["weighted_latency_seconds"],
        duration_seconds=perf_counter() - started,
        seed=SEED,
        message=f"measured {len(measurements)} real SQLite index subsets under a {STORAGE_BUDGET_BYTES}-byte budget",
        metrics={
            "baseline_weighted_latency_seconds": baseline["weighted_latency_seconds"],
            "greedy_weighted_latency_seconds": greedy["weighted_latency_seconds"],
            "exact_weighted_latency_seconds": exact["weighted_latency_seconds"],
            "exact_storage_bytes": exact["storage_bytes"],
            "all_subset_results_equal": True,
        },
        metadata=environment_metadata(),
    )
