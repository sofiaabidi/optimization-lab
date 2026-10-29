from pathlib import Path

import pytest

from optlab.track_g import parse_benchmark_file, parse_benchmark_text, summarize_benchmarks


def test_captured_real_benchmarks_have_identical_fixed_cpu_work_and_expected_scheduler():
    root = Path(__file__).resolve().parents[1]
    baseline = parse_benchmark_file(root / "results/g/baseline_benchmark.log", "baseline")
    optimized = parse_benchmark_file(root / "results/g/optimized_benchmark.log", "optimized")
    assert len(baseline) == len(optimized) == 9
    assert {row["scheduler"] for row in baseline} == {0}
    assert {row["scheduler"] for row in optimized} == {1}
    assert {row["total"] for row in baseline + optimized if row["workload"] == "cpu"} == {330000000}


def test_measured_priority_response_improves_but_cpu_makespan_does_not():
    root = Path(__file__).resolve().parents[1]
    rows = parse_benchmark_file(root / "results/g/baseline_benchmark.log", "baseline")
    rows += parse_benchmark_file(root / "results/g/optimized_benchmark.log", "optimized")
    summaries = summarize_benchmarks(rows)
    get = lambda variant, workload: next(
        row for row in summaries if row["variant"] == variant and row["workload"] == workload
    )
    assert get("optimized", "cpu")["median_response_ticks"] < get("baseline", "cpu")["median_response_ticks"]
    assert get("optimized", "mixed")["median_response_ticks"] < get("baseline", "mixed")["median_response_ticks"]
    assert get("optimized", "cpu")["median_makespan_ticks"] >= get("baseline", "cpu")["median_makespan_ticks"]


def test_parser_rejects_incomplete_or_unverified_output():
    with pytest.raises(ValueError, match="pass marker"):
        parse_benchmark_text("RESULT workload=cpu repeat=0", "bad")
    with pytest.raises(ValueError, match="three repeats"):
        parse_benchmark_text("SCHEDBENCH PASS\n", "bad")
