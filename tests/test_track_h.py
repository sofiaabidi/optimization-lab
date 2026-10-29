import shutil
import sqlite3
from pathlib import Path

from optlab.track_h import (
    CANDIDATE_INDEXES,
    benchmark_subsets,
    create_database,
    exact_subset_ilp,
    greedy_select,
    workload,
)


def test_seeded_database_has_documented_counts_and_valid_relations(tmp_path: Path):
    database = tmp_path / "campus.sqlite"
    duplicate = tmp_path / "campus-duplicate.sqlite"
    counts = create_database(database, student_count=300)
    create_database(duplicate, student_count=300)
    assert counts == {"departments": 12, "courses": 240, "students": 300, "enrollments": 1800}
    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute("SELECT COUNT(DISTINCT term) FROM enrollments").fetchone()[0] == 4
        assert connection.execute("SELECT MIN(grade), MAX(grade) FROM enrollments").fetchone() == (1.2, 4.0)
        sample = connection.execute(
            "SELECT student_id, course_id, term, grade FROM enrollments ORDER BY id LIMIT 40"
        ).fetchall()
    with sqlite3.connect(duplicate) as connection:
        duplicate_sample = connection.execute(
            "SELECT student_id, course_id, term, grade FROM enrollments ORDER BY id LIMIT 40"
        ).fetchall()
    assert duplicate_sample == sample


def test_real_sqlite_subsets_preserve_results_and_change_plans(tmp_path: Path):
    database = tmp_path / "baseline.sqlite"
    create_database(database, student_count=300)
    specs = workload(student_count=300)
    measurements, raw, plans = benchmark_subsets(
        database,
        tmp_path,
        CANDIDATE_INDEXES[:3],
        specs,
        repeats=1,
    )
    assert len(measurements) == 8
    assert len(raw) == 8 * 5 * 3
    baseline = next(row for row in measurements if not row["indexes"])
    assert all(row["checksums"] == baseline["checksums"] for row in measurements)
    assert any(plans[row["subset"]] != plans["none"] for row in measurements if row["indexes"])
    assert all(row["storage_bytes"] >= 0 for row in measurements)


def test_greedy_is_conditional_and_exact_ilp_matches_feasible_oracle():
    def row(indexes, cost, objective):
        return {
            "subset": "+".join(indexes) if indexes else "none",
            "indexes": tuple(indexes),
            "storage_bytes": cost,
            "weighted_latency_seconds": objective,
        }

    measurements = [
        row((), 0, 10.0),
        row(("a",), 4, 7.0),
        row(("b",), 4, 8.0),
        row(("c",), 5, 9.0),
        row(("a", "b"), 8, 6.5),
        row(("a", "c"), 9, 5.0),
        row(("b", "c"), 9, 3.0),
        row(("a", "b", "c"), 13, 2.0),
    ]
    greedy = greedy_select(measurements, budget_bytes=9)
    exact = exact_subset_ilp(measurements, budget_bytes=9)
    assert greedy["subset"] == "a+c"
    assert exact["subset"] == "b+c"
    assert exact["weighted_latency_seconds"] == 3.0


def test_database_copy_does_not_mutate_preserved_baseline(tmp_path: Path):
    baseline = tmp_path / "baseline.sqlite"
    copy = tmp_path / "copy.sqlite"
    create_database(baseline, student_count=300)
    shutil.copy2(baseline, copy)
    with sqlite3.connect(copy) as connection:
        connection.execute(CANDIDATE_INDEXES[0].sql)
    with sqlite3.connect(baseline) as connection:
        added = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
        ).fetchall()
    assert added == []
