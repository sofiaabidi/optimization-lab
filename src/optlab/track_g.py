from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from statistics import median
from time import perf_counter
from typing import Any

from .experiment import environment_metadata
from .models import ExperimentResult, RunStatus
from .plotting import write_bar_svg

UPSTREAM_SHA = "e93dabeb98431235c6e1a101cb96c73c923fdbc4"
RESULT_PATTERN = re.compile(r"^RESULT (?P<fields>.+)$", re.MULTILINE)
EXPECTED_WORKLOADS = {"cpu", "mixed", "fairness"}


def parse_benchmark_text(text: str, variant: str) -> list[dict[str, Any]]:
    if "SCHEDBENCH PASS" not in text:
        raise ValueError(f"{variant} benchmark has no pass marker")
    rows: list[dict[str, Any]] = []
    for match in RESULT_PATTERN.finditer(text.replace("\r", "")):
        fields = dict(field.split("=", 1) for field in match.group("fields").split())
        row: dict[str, Any] = {"variant": variant, "workload": fields.pop("workload")}
        row.update({name: int(value) for name, value in fields.items()})
        maximum = int(row["max"])
        makespan = int(row["makespan"])
        row["fairness_min_max"] = 1.0 if maximum == 0 else int(row["min"]) / maximum
        row["throughput_work_per_tick"] = None if makespan == 0 else int(row["total"]) / makespan
        rows.append(row)
    if len(rows) != 9 or {row["workload"] for row in rows} != EXPECTED_WORKLOADS:
        raise ValueError(f"{variant} benchmark must contain three repeats of three workloads")
    for workload in EXPECTED_WORKLOADS:
        repeats = sorted(row["repeat"] for row in rows if row["workload"] == workload)
        if repeats != [0, 1, 2]:
            raise ValueError(f"{variant}/{workload} repeats are incomplete")
    return rows


def parse_benchmark_file(path: Path, variant: str) -> list[dict[str, Any]]:
    return parse_benchmark_text(path.read_text(encoding="utf-8", errors="replace"), variant)


def summarize_benchmarks(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries = []
    for variant in ("baseline", "optimized"):
        for workload in ("cpu", "mixed", "fairness"):
            selected = [row for row in rows if row["variant"] == variant and row["workload"] == workload]
            summaries.append(
                {
                    "variant": variant,
                    "workload": workload,
                    "median_response_ticks": float(median(row["response"] for row in selected)),
                    "median_makespan_ticks": float(median(row["makespan"] for row in selected)),
                    "median_total_work": float(median(row["total"] for row in selected)),
                    "median_throughput_work_per_tick": float(median(row["throughput_work_per_tick"] for row in selected)),
                    "median_fairness_min_max": float(median(row["fairness_min_max"] for row in selected)),
                    "median_high_dispatches": float(median(row["high_dispatches"] for row in selected)),
                    "median_high_runtime_ticks": float(median(row["high_runtime"] for row in selected)),
                }
            )
    return summaries


def compare_summaries(summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    metrics = (
        "median_response_ticks",
        "median_makespan_ticks",
        "median_throughput_work_per_tick",
        "median_fairness_min_max",
    )
    for workload in ("cpu", "mixed", "fairness"):
        baseline = next(row for row in summaries if row["variant"] == "baseline" and row["workload"] == workload)
        optimized = next(row for row in summaries if row["variant"] == "optimized" and row["workload"] == workload)
        for metric in metrics:
            baseline_value = float(baseline[metric])
            optimized_value = float(optimized[metric])
            rows.append(
                {
                    "workload": workload,
                    "metric": metric,
                    "baseline": baseline_value,
                    "optimized": optimized_value,
                    "absolute_change": optimized_value - baseline_value,
                    "relative_change": None if baseline_value == 0 else (optimized_value - baseline_value) / baseline_value,
                }
            )
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("cannot write empty CSV")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _verified_log(path: Path, marker: str) -> bool:
    return path.exists() and marker in path.read_text(encoding="utf-8", errors="replace")


def run_experiment(profile: str = "quick", output_dir: Path | None = None) -> ExperimentResult:
    if profile not in {"quick", "full"}:
        raise ValueError("profile must be quick or full")
    if profile == "full":
        return ExperimentResult(
            track="g",
            profile=profile,
            status=RunStatus.NOT_RUN,
            message="full xv6 benchmark profile was not run; use the documented external workflow",
        )
    started = perf_counter()
    output_dir = output_dir or Path("results/g")
    baseline_log = output_dir / "baseline_benchmark.log"
    optimized_log = output_dir / "optimized_benchmark.log"
    rows = parse_benchmark_file(baseline_log, "baseline") + parse_benchmark_file(optimized_log, "optimized")
    if any(row["scheduler"] != 0 for row in rows if row["variant"] == "baseline"):
        raise RuntimeError("baseline unexpectedly reports the priority scheduler")
    if any(row["scheduler"] != 1 for row in rows if row["variant"] == "optimized"):
        raise RuntimeError("optimized benchmark did not exercise the priority scheduler")
    if any(row["total"] != 330000000 for row in rows if row["workload"] == "cpu"):
        raise RuntimeError("CPU workload did not complete identical fixed work")

    test_logs = {
        "upstream_baseline": output_dir / "baseline_boot_usertests.log",
        "priority_change": output_dir / "priority_usertests.log",
        "accounting_change": output_dir / "accounting_usertests.log",
    }
    if not all(_verified_log(path, "ALL TESTS PASSED") for path in test_logs.values()):
        raise RuntimeError("one or more required xv6 usertests logs lack the pass marker")
    if not all(_verified_log(path, "xv6 kernel is booting") for path in test_logs.values()):
        raise RuntimeError("one or more required logs lack a real xv6 boot marker")

    summaries = summarize_benchmarks(rows)
    comparisons = compare_summaries(summaries)
    _write_csv(output_dir / "benchmark.csv", rows)
    _write_csv(output_dir / "benchmark_summary.csv", summaries)
    _write_csv(output_dir / "comparison.csv", comparisons)

    response_rows = [row for row in summaries if row["workload"] in {"cpu", "mixed"}]
    write_bar_svg(
        [f"{row['variant']} {row['workload']}" for row in response_rows],
        [float(row["median_response_ticks"]) for row in response_rows],
        output_dir / "response_ticks.svg",
        "Track G median high-priority response (lower is better)",
    )

    baseline_cpu = next(row for row in summaries if row["variant"] == "baseline" and row["workload"] == "cpu")
    optimized_cpu = next(row for row in summaries if row["variant"] == "optimized" and row["workload"] == "cpu")
    baseline_mixed = next(row for row in summaries if row["variant"] == "baseline" and row["workload"] == "mixed")
    optimized_mixed = next(row for row in summaries if row["variant"] == "optimized" and row["workload"] == "mixed")
    summary = {
        "profile": "quick",
        "date": "2026-10-29",
        "environment": environment_metadata(),
        "provenance": {
            "repository": "https://github.com/mit-pdos/xv6-riscv.git",
            "upstream_sha": UPSTREAM_SHA,
            "upstream_subject": "tx_busy",
            "license": "MIT; upstream LICENSE retained in checkout",
        },
        "toolchain": {
            "qemu": "QEMU 10.2.1 (Ubuntu 1:10.2.1+ds-1ubuntu3.3)",
            "gcc": "riscv64-unknown-elf-gcc 14.2.0",
            "binutils": "riscv64-unknown-elf-ld 2.45.50.20251209",
            "make": "GNU Make 4.4.1",
        },
        "kernel_features": [
            "strict priorities 0..3 with priority inheritance and per-CPU round-robin tie breaking",
            "setpriority system call",
            "dispatch/runtime-tick accounting exposed by getpstats system call",
        ],
        "verification": {
            "upstream_baseline_boot_and_usertests": True,
            "priority_change_boot_and_usertests": True,
            "accounting_change_boot_and_usertests": True,
            "benchmark_baseline_pass": True,
            "benchmark_optimized_pass": True,
            "qemu_boot_cpus": 3,
            "benchmark_cpus": 1,
            "full_profile_status": "NOT RUN",
        },
        "key_results": {
            "cpu_response_ticks_baseline": baseline_cpu["median_response_ticks"],
            "cpu_response_ticks_optimized": optimized_cpu["median_response_ticks"],
            "cpu_makespan_ticks_baseline": baseline_cpu["median_makespan_ticks"],
            "cpu_makespan_ticks_optimized": optimized_cpu["median_makespan_ticks"],
            "mixed_response_ticks_baseline": baseline_mixed["median_response_ticks"],
            "mixed_response_ticks_optimized": optimized_mixed["median_response_ticks"],
        },
        "limitations": [
            "Strict priorities have no aging and can starve continuously runnable low-priority processes.",
            "One-CPU benchmarks isolate scheduling policy but do not measure multicore scalability.",
            "Global uptime ticks have 0.1-second resolution, and only three repeats were run.",
            "Accounting runtime ticks count timer quanta, not hardware cycles or time spent between voluntary sleeps.",
            "The optimized CPU makespan did not improve; latency gains trade against low-priority progress.",
        ],
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return ExperimentResult(
        track="g",
        profile="quick",
        status=RunStatus.DONE,
        method="real xv6 strict-priority scheduler with accounting",
        objective=float(optimized_cpu["median_response_ticks"]),
        duration_seconds=perf_counter() - started,
        message=f"validated captured real-QEMU artifacts in {output_dir}",
        metrics={
            "baseline_cpu_response_ticks": baseline_cpu["median_response_ticks"],
            "optimized_cpu_response_ticks": optimized_cpu["median_response_ticks"],
            "baseline_mixed_response_ticks": baseline_mixed["median_response_ticks"],
            "optimized_mixed_response_ticks": optimized_mixed["median_response_ticks"],
            "all_three_usertests_runs_passed": True,
        },
        metadata=environment_metadata(),
    )
