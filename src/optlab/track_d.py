from __future__ import annotations

import csv
import itertools
import json
import math
import os
import threading
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from multiprocessing import get_context
from pathlib import Path
from time import perf_counter
from typing import Any, Iterable

import numpy as np

from .experiment import environment_metadata
from .models import ExperimentResult, RunStatus
from .plotting import write_bar_svg

SEED = 2026


def coverage_sets() -> tuple[frozenset[int], ...]:
    return (
        frozenset({0, 1, 2, 3}),
        frozenset({2, 3, 4, 5}),
        frozenset({5, 6, 7}),
        frozenset({7, 8, 9}),
        frozenset({0, 9, 10}),
        frozenset({4, 10, 11}),
    )


def coverage_value(selected: Iterable[int], candidates: tuple[frozenset[int], ...] | None = None) -> int:
    candidates = candidates or coverage_sets()
    covered: set[int] = set()
    for index in selected:
        covered.update(candidates[index])
    return len(covered)


def greedy_coverage(budget: int, candidates: tuple[frozenset[int], ...] | None = None) -> tuple[tuple[int, ...], int]:
    candidates = candidates or coverage_sets()
    selected: list[int] = []
    while len(selected) < budget:
        available = [index for index in range(len(candidates)) if index not in selected]
        choice = max(
            available,
            key=lambda index: (coverage_value((*selected, index), candidates) - coverage_value(selected, candidates), -index),
        )
        selected.append(choice)
    return tuple(selected), coverage_value(selected, candidates)


def exhaustive_coverage(budget: int, candidates: tuple[frozenset[int], ...] | None = None) -> tuple[tuple[int, ...], int]:
    candidates = candidates or coverage_sets()
    best = max(
        itertools.combinations(range(len(candidates)), budget),
        key=lambda choice: (coverage_value(choice, candidates), tuple(-index for index in choice)),
    )
    return best, coverage_value(best, candidates)


def verify_diminishing_returns(candidates: tuple[frozenset[int], ...] | None = None) -> dict[str, int | bool]:
    candidates = candidates or coverage_sets()
    count = len(candidates)
    checks = 0
    violations = 0
    subsets = [frozenset(index for index in range(count) if mask & (1 << index)) for mask in range(1 << count)]
    for smaller in subsets:
        for larger in subsets:
            if not smaller.issubset(larger):
                continue
            for element in range(count):
                if element in larger:
                    continue
                checks += 1
                small_gain = coverage_value((*smaller, element), candidates) - coverage_value(smaller, candidates)
                large_gain = coverage_value((*larger, element), candidates) - coverage_value(larger, candidates)
                if small_gain < large_gain:
                    violations += 1
    return {"checks": checks, "violations": violations, "passed": violations == 0}


def _cpu_task(iterations: int) -> tuple[int, float, int, int]:
    started = perf_counter()
    accumulator = _cpu_checksum(iterations)
    return accumulator, perf_counter() - started, os.getpid(), iterations


def _cpu_checksum(iterations: int) -> int:
    accumulator = 0
    for value in range(iterations):
        accumulator = (accumulator + (value * value + 17 * value + 23) % 104729) % 1_000_000_007
    return accumulator


def measure_scaling(worker_counts: tuple[int, ...] = (1, 2, 4), repeats: int = 3, task_count: int = 24, iterations: int = 120_000) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    tasks = [iterations] * task_count
    for workers in worker_counts:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            list(pool.map(_cpu_task, [1_000] * workers))
            for repeat in range(repeats):
                started = perf_counter()
                results = list(pool.map(_cpu_task, tasks, chunksize=1))
                wall = perf_counter() - started
                rows.append(
                    {
                        "workers": workers,
                        "repeat": repeat,
                        "wall_seconds": wall,
                        "checksum": sum(result[0] for result in results),
                        "distinct_worker_pids": len({result[2] for result in results}),
                        "task_compute_seconds_sum": sum(result[1] for result in results),
                    }
                )
    baseline = float(np.median([row["wall_seconds"] for row in rows if row["workers"] == 1]))
    for row in rows:
        row["speedup_vs_1_worker_median"] = baseline / row["wall_seconds"]
        row["efficiency"] = row["speedup_vs_1_worker_median"] / row["workers"]
    return rows


def measure_scheduling(workers: int = 4) -> list[dict[str, Any]]:
    tasks = [70_000] * 12 + [450_000] * 4
    rows = []
    for policy, chunksize in (("static_contiguous_chunks", math.ceil(len(tasks) / workers)), ("dynamic_shared_queue", 1)):
        with ProcessPoolExecutor(max_workers=workers) as pool:
            list(pool.map(_cpu_task, [1_000] * workers))
            started = perf_counter()
            results = list(pool.map(_cpu_task, tasks, chunksize=chunksize))
            wall = perf_counter() - started
        per_worker: dict[int, float] = {}
        for _, duration, pid, _ in results:
            per_worker[pid] = per_worker.get(pid, 0.0) + duration
        loads = list(per_worker.values())
        rows.append(
            {
                "policy": policy,
                "workers": workers,
                "wall_seconds": wall,
                "makespan_seconds": max(loads),
                "mean_worker_compute_seconds": float(np.mean(loads)),
                "load_imbalance_max_over_mean": max(loads) / float(np.mean(loads)),
                "distinct_worker_pids": len(per_worker),
                "checksum": sum(result[0] for result in results),
                "interpretation": "real process-pool timing; dynamic queue is a work-stealing analogue, not a per-worker deque implementation",
            }
        )
    return rows


def _deque_worker(
    worker: int,
    tasks: list[int],
    deque_buffers: list[Any],
    left_indices: list[Any],
    right_indices: list[Any],
    locks: list[Any],
    allow_stealing: bool,
    ready_queue: Any,
    start_event: Any,
    output_queue: Any,
) -> None:
    ready_queue.put(worker)
    start_event.wait()
    completed: list[int] = []
    checksum = 0
    compute_seconds = 0.0
    stolen = 0
    while True:
        task = None
        with locks[worker]:
            if left_indices[worker].value < right_indices[worker].value:
                right_indices[worker].value -= 1
                task = deque_buffers[worker][right_indices[worker].value]
        if task is None and allow_stealing:
            for offset in range(1, len(deque_buffers)):
                victim = (worker + offset) % len(deque_buffers)
                with locks[victim]:
                    if left_indices[victim].value < right_indices[victim].value:
                        task = deque_buffers[victim][left_indices[victim].value]
                        left_indices[victim].value += 1
                if task is not None:
                    stolen += 1
                    break
        if task is None:
            break
        task_id = task
        iterations = tasks[task_id]
        value, duration, _, _ = _cpu_task(iterations)
        completed.append(task_id)
        checksum += value
        compute_seconds += duration
    output_queue.put(
        {
            "worker": worker,
            "pid": os.getpid(),
            "tasks_executed": len(completed),
            "stolen_tasks": stolen,
            "task_ids": completed,
            "checksum": checksum,
            "compute_seconds": compute_seconds,
        }
    )


def _run_deque_schedule(tasks: list[int], workers: int, allow_stealing: bool) -> dict[str, Any]:
    if workers < 2 or len(tasks) < workers:
        raise ValueError("deque scheduling requires at least two workers and one task per worker")
    context = get_context("fork")
    assignments = [list(map(int, chunk)) for chunk in np.array_split(np.arange(len(tasks)), workers)]
    deque_buffers = [context.RawArray("i", assignment) for assignment in assignments]
    left_indices = [context.RawValue("i", 0) for _ in range(workers)]
    right_indices = [context.RawValue("i", len(assignment)) for assignment in assignments]
    locks = [context.Lock() for _ in range(workers)]
    ready_queue = context.Queue()
    output_queue = context.Queue()
    start_event = context.Event()
    processes = [
        context.Process(
            target=_deque_worker,
            args=(
                worker,
                tasks,
                deque_buffers,
                left_indices,
                right_indices,
                locks,
                allow_stealing,
                ready_queue,
                start_event,
                output_queue,
            ),
        )
        for worker in range(workers)
    ]
    for process in processes:
        process.start()
    for _ in processes:
        ready_queue.get(timeout=10)
    started = perf_counter()
    start_event.set()
    details = [output_queue.get(timeout=30) for _ in processes]
    wall_seconds = perf_counter() - started
    for process in processes:
        process.join(timeout=10)
        if process.exitcode != 0:
            raise RuntimeError(f"deque worker exited with code {process.exitcode}")
    completed_ids = [task_id for detail in details for task_id in detail["task_ids"]]
    expected_checksum = sum(_cpu_checksum(iterations) for iterations in tasks)
    loads = [float(detail["compute_seconds"]) for detail in details]
    return {
        "policy": "per_worker_deques_with_stealing" if allow_stealing else "per_worker_deques_static",
        "workers": workers,
        "tasks": len(tasks),
        "wall_seconds": wall_seconds,
        "makespan_compute_seconds": max(loads),
        "mean_worker_compute_seconds": float(np.mean(loads)),
        "load_imbalance_max_over_mean": max(loads) / float(np.mean(loads)),
        "stolen_tasks": sum(int(detail["stolen_tasks"]) for detail in details),
        "distinct_worker_pids": len({int(detail["pid"]) for detail in details}),
        "every_task_once": sorted(completed_ids) == list(range(len(tasks))),
        "checksum_matches": sum(int(detail["checksum"]) for detail in details) == expected_checksum,
        "owner_end": "right",
        "thief_end": "left" if allow_stealing else "disabled",
        "worker_task_counts": json.dumps(
            {int(detail["worker"]): int(detail["tasks_executed"]) for detail in details},
            sort_keys=True,
        ),
    }


def measure_work_stealing(workers: int = 4, tasks: list[int] | None = None) -> list[dict[str, Any]]:
    tasks = tasks or ([300_000] * workers + [35_000] * (workers * 3))
    return [
        _run_deque_schedule(tasks, workers, allow_stealing=False),
        _run_deque_schedule(tasks, workers, allow_stealing=True),
    ]


def measure_synchronization(workers: int = 4, increments: int = 25_000) -> list[dict[str, Any]]:
    counter = [0]
    lock = threading.Lock()

    def locked_increment() -> None:
        for _ in range(increments):
            with lock:
                counter[0] += 1

    started = perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(lambda _: locked_increment(), range(workers)))
    locked_time = perf_counter() - started

    def local_increment() -> int:
        local = 0
        for _ in range(increments):
            local += 1
        return local

    started = perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        local_total = sum(pool.map(lambda _: local_increment(), range(workers)))
    local_time = perf_counter() - started
    expected = workers * increments
    if counter[0] != expected or local_total != expected:
        raise AssertionError("synchronization benchmark produced an incorrect count")
    return [
        {"variant": "shared_lock_every_increment", "wall_seconds": locked_time, "result": counter[0], "workers": workers},
        {"variant": "thread_local_then_reduce", "wall_seconds": local_time, "result": local_total, "workers": workers},
    ]


def _payload_checksum(payload: bytes) -> tuple[int, int]:
    boundary = (payload[0] + payload[-1]) if payload else 0
    return len(payload) + boundary, os.getpid()


def measure_communication(workers: int = 2, messages: int = 12) -> list[dict[str, Any]]:
    rows = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        list(pool.map(_payload_checksum, [b"warmup"] * workers))
        for label, payload in (("small_64B", bytes(range(64))), ("large_1MiB", bytes([7]) * (1024 * 1024))):
            started = perf_counter()
            results = list(pool.map(_payload_checksum, [payload] * messages, chunksize=1))
            wall = perf_counter() - started
            transferred = len(payload) * messages
            rows.append(
                {
                    "payload": label,
                    "payload_bytes": len(payload),
                    "messages": messages,
                    "total_payload_bytes": transferred,
                    "wall_seconds": wall,
                    "effective_mib_per_second": transferred / (1024 * 1024) / wall,
                    "distinct_worker_pids": len({pid for _, pid in results}),
                    "checksum": sum(value for value, _ in results),
                }
            )
    return rows


def measure_locality(elements: int = 400_000, repeats: int = 3) -> list[dict[str, Any]]:
    data = np.arange(elements * 4, dtype=np.float64)
    contiguous = np.arange(elements)
    random_indices = np.random.default_rng(SEED).choice(len(data), size=elements, replace=False)
    rows = []
    for label, indices in (("contiguous", contiguous), ("random_gather", random_indices)):
        for repeat in range(repeats):
            started = perf_counter()
            checksum = float(np.sum(data[indices]))
            rows.append({"access": label, "repeat": repeat, "wall_seconds": perf_counter() - started, "checksum": checksum})
    return rows


def _linear_gradient_chunk(arguments: tuple[np.ndarray, np.ndarray, np.ndarray]) -> tuple[np.ndarray, float, int, int]:
    x, y, weights = arguments
    residual = x @ weights - y
    return x.T @ residual, float(residual @ residual), len(x), os.getpid()


def data_parallel_demo(workers: int = 2, samples: int = 2_000, features: int = 8) -> dict[str, Any]:
    rng = np.random.default_rng(SEED)
    x = rng.normal(size=(samples, features))
    y = rng.normal(size=samples)
    weights = rng.normal(size=features)
    started = perf_counter()
    serial_gradient, serial_squared, count, _ = _linear_gradient_chunk((x, y, weights))
    serial_gradient /= count
    serial_loss = 0.5 * serial_squared / count
    serial_time = perf_counter() - started
    chunks = [(x_chunk, y_chunk, weights) for x_chunk, y_chunk in zip(np.array_split(x, workers), np.array_split(y, workers), strict=True)]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        list(pool.map(_cpu_task, [1_000] * workers))
        started = perf_counter()
        results = list(pool.map(_linear_gradient_chunk, chunks))
        parallel_time = perf_counter() - started
    total = sum(result[2] for result in results)
    parallel_gradient = sum((result[0] for result in results), start=np.zeros(features)) / total
    parallel_loss = 0.5 * sum(result[1] for result in results) / total
    return {
        "pattern": "data_parallel",
        "serial_seconds": serial_time,
        "parallel_seconds": parallel_time,
        "max_abs_error": float(max(np.max(np.abs(serial_gradient - parallel_gradient)), abs(serial_loss - parallel_loss))),
        "worker_pids": sorted({result[3] for result in results}),
        "actually_parallel": len({result[3] for result in results}) > 1,
        "communication": "row shards sent to processes; gradients and loss sums returned and reduced",
    }


def _prediction_block(arguments: tuple[np.ndarray, np.ndarray]) -> tuple[np.ndarray, int]:
    x_block, weight_block = arguments
    return x_block @ weight_block, os.getpid()


def model_parallel_demo(workers: int = 2, samples: int = 2_000, features: int = 8) -> dict[str, Any]:
    rng = np.random.default_rng(SEED + 1)
    x = rng.normal(size=(samples, features))
    weights = rng.normal(size=features)
    started = perf_counter()
    serial = x @ weights
    serial_time = perf_counter() - started
    x_blocks = np.array_split(x, workers, axis=1)
    weight_blocks = np.array_split(weights, workers)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        list(pool.map(_cpu_task, [1_000] * workers))
        started = perf_counter()
        results = list(pool.map(_prediction_block, zip(x_blocks, weight_blocks, strict=True)))
        parallel_time = perf_counter() - started
    combined = sum((result[0] for result in results), start=np.zeros(samples))
    return {
        "pattern": "model_parallel",
        "serial_seconds": serial_time,
        "parallel_seconds": parallel_time,
        "max_abs_error": float(np.max(np.abs(serial - combined))),
        "worker_pids": sorted({result[1] for result in results}),
        "actually_parallel": len({result[1] for result in results}) > 1,
        "communication": "feature/parameter blocks sent to processes; partial predictions returned and summed",
    }


def _pipeline_transform(value: int, rounds: int, salt: int) -> int:
    result = value
    for index in range(rounds):
        result = (result * 1664525 + 1013904223 + salt + index) & 0xFFFFFFFF
    return result


def _pipeline_stage(input_queue: Any, output_queue: Any, rounds: int, salt: int, ready: Any) -> None:
    ready.set()
    while True:
        item = input_queue.get()
        if item is None:
            output_queue.put(None)
            return
        index, value, pids = item
        output_queue.put((index, _pipeline_transform(value, rounds, salt), (*pids, os.getpid())))


def pipeline_parallel_demo(items: int = 24, rounds: int = 35_000) -> dict[str, Any]:
    inputs = list(range(items))
    started = perf_counter()
    serial = [_pipeline_transform(_pipeline_transform(value, rounds, 11), rounds, 29) for value in inputs]
    serial_time = perf_counter() - started
    context = get_context("fork")
    first_queue, second_queue, output_queue = context.Queue(), context.Queue(), context.Queue()
    first_ready, second_ready = context.Event(), context.Event()
    first = context.Process(target=_pipeline_stage, args=(first_queue, second_queue, rounds, 11, first_ready))
    second = context.Process(target=_pipeline_stage, args=(second_queue, output_queue, rounds, 29, second_ready))
    first.start()
    second.start()
    first_ready.wait()
    second_ready.wait()
    started = perf_counter()
    for index, value in enumerate(inputs):
        first_queue.put((index, value, ()))
    first_queue.put(None)
    received = []
    while True:
        item = output_queue.get()
        if item is None:
            break
        received.append(item)
    parallel_time = perf_counter() - started
    first.join()
    second.join()
    received.sort(key=lambda item: item[0])
    parallel = [item[1] for item in received]
    pids = sorted({pid for item in received for pid in item[2]})
    return {
        "pattern": "pipeline_parallel",
        "serial_seconds": serial_time,
        "parallel_seconds": parallel_time,
        "max_abs_error": 0.0 if serial == parallel else float("inf"),
        "worker_pids": pids,
        "actually_parallel": len(pids) == 2,
        "communication": "two live process stages connected by queues; process startup excluded, queue transfer included",
    }


def parallel_interpretation(scaling_rows: list[dict[str, Any]]) -> dict[str, float | str]:
    workers = max(int(row["workers"]) for row in scaling_rows)
    baseline = float(np.median([row["wall_seconds"] for row in scaling_rows if row["workers"] == 1]))
    parallel = float(np.median([row["wall_seconds"] for row in scaling_rows if row["workers"] == workers]))
    speedup = baseline / parallel
    effective_parallel_fraction = (1 - 1 / speedup) / (1 - 1 / workers) if workers > 1 else 0.0
    effective_serial_fraction = 1 - effective_parallel_fraction
    gustafson_scaled = workers - effective_serial_fraction * (workers - 1)
    return {
        "workers": workers,
        "measured_speedup": speedup,
        "measured_efficiency": speedup / workers,
        "amdahl_inferred_parallel_fraction": effective_parallel_fraction,
        "gustafson_scaled_speedup_from_inferred_fraction": gustafson_scaled,
        "warning": "Derived from one bounded measurement; overhead can make inferred fractions fall outside physical bounds, so this is interpretation, not extrapolation.",
    }


def make_federated_data(seed: int = SEED) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    x = rng.normal(size=(320, 2))
    logits = 1.4 * x[:, 0] - 1.1 * x[:, 1] + rng.normal(scale=0.45, size=len(x))
    y = (logits > 0).astype(float)
    permutation = rng.permutation(len(x))
    train_indices, test_indices = permutation[:240], permutation[240:]
    x_train = np.column_stack((x[train_indices], np.ones(len(train_indices))))
    y_train = y[train_indices]
    x_test = np.column_stack((x[test_indices], np.ones(len(test_indices))))
    y_test = y[test_indices]
    ordering = np.argsort(x_train[:, 0] + 2.0 * y_train)
    client_indices = [indices.copy() for indices in np.array_split(ordering, 4)]
    return {"x_train": x_train, "y_train": y_train, "x_test": x_test, "y_test": y_test, "clients": client_indices}


def _sigmoid(values: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(values, -30, 30)))


def logistic_loss_gradient(x: np.ndarray, y: np.ndarray, weights: np.ndarray) -> tuple[float, np.ndarray]:
    probabilities = _sigmoid(x @ weights)
    epsilon = 1e-12
    loss = -float(np.mean(y * np.log(probabilities + epsilon) + (1 - y) * np.log(1 - probabilities + epsilon)))
    gradient = x.T @ (probabilities - y) / len(x)
    return loss, gradient


def classification_accuracy(x: np.ndarray, y: np.ndarray, weights: np.ndarray) -> float:
    return float(np.mean((_sigmoid(x @ weights) >= 0.5) == y))


def centralized_training(data: dict[str, Any], steps: int = 50, learning_rate: float = 0.3) -> dict[str, Any]:
    weights = np.zeros(data["x_train"].shape[1])
    started = perf_counter()
    history = []
    for step in range(steps):
        loss, gradient = logistic_loss_gradient(data["x_train"], data["y_train"], weights)
        history.append({"step": step, "loss": loss})
        weights -= learning_rate * gradient
    final_loss, _ = logistic_loss_gradient(data["x_train"], data["y_train"], weights)
    return {
        "method": "centralized",
        "local_steps": 0,
        "rounds": steps,
        "gradient_evaluations": steps,
        "communication_bytes": 0,
        "train_loss": final_loss,
        "test_accuracy": classification_accuracy(data["x_test"], data["y_test"], weights),
        "duration_seconds": perf_counter() - started,
        "weights": weights.tolist(),
        "history": history,
    }


def fedavg_training(data: dict[str, Any], local_steps: int, rounds: int, learning_rate: float = 0.3) -> dict[str, Any]:
    weights = np.zeros(data["x_train"].shape[1])
    clients = data["clients"]
    parameter_bytes = weights.nbytes
    history = []
    started = perf_counter()
    for round_index in range(rounds):
        local_models = []
        client_sizes = []
        for indices in clients:
            local = weights.copy()
            for _ in range(local_steps):
                _, gradient = logistic_loss_gradient(data["x_train"][indices], data["y_train"][indices], local)
                local -= learning_rate * gradient
            local_models.append(local)
            client_sizes.append(len(indices))
        weights = np.average(np.stack(local_models), axis=0, weights=client_sizes)
        loss, _ = logistic_loss_gradient(data["x_train"], data["y_train"], weights)
        history.append({"step": round_index, "loss": loss})
    final_loss, _ = logistic_loss_gradient(data["x_train"], data["y_train"], weights)
    return {
        "method": "fedavg",
        "local_steps": local_steps,
        "rounds": rounds,
        "gradient_evaluations": rounds * local_steps * len(clients),
        "communication_bytes": rounds * len(clients) * parameter_bytes * 2,
        "train_loss": final_loss,
        "test_accuracy": classification_accuracy(data["x_test"], data["y_test"], weights),
        "duration_seconds": perf_counter() - started,
        "weights": weights.tolist(),
        "history": history,
    }


def mgda_coefficient(first_gradient: np.ndarray, second_gradient: np.ndarray) -> float:
    difference = first_gradient - second_gradient
    denominator = float(difference @ difference)
    if denominator < 1e-15:
        return 0.5
    return float(np.clip(-(difference @ second_gradient) / denominator, 0.0, 1.0))


def make_multitask_data(seed: int = SEED) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    x = rng.normal(size=(128, 2))
    task_one = x @ np.array([2.0, 0.5]) + rng.normal(scale=0.1, size=len(x))
    task_two = x @ np.array([-1.0, 2.0]) + rng.normal(scale=0.25, size=len(x))
    return x, task_one, task_two


def _regression_loss_gradient(x: np.ndarray, target: np.ndarray, weights: np.ndarray) -> tuple[float, np.ndarray]:
    residual = x @ weights - target
    return 0.5 * float(np.mean(residual**2)), x.T @ residual / len(x)


def multitask_training(method: str, steps: int = 120, learning_rate: float = 0.08) -> dict[str, Any]:
    if method not in {"equal", "mgda", "gradnorm"}:
        raise ValueError(f"unknown multi-task method: {method}")
    x, first_target, second_target = make_multitask_data()
    weights = np.zeros(x.shape[1])
    task_weights = np.ones(2)
    initial_losses = np.array([_regression_loss_gradient(x, first_target, weights)[0], _regression_loss_gradient(x, second_target, weights)[0]])
    history = []
    started = perf_counter()
    for step in range(steps):
        first_loss, first_gradient = _regression_loss_gradient(x, first_target, weights)
        second_loss, second_gradient = _regression_loss_gradient(x, second_target, weights)
        if method == "equal":
            coefficients = np.array([0.5, 0.5])
        elif method == "mgda":
            alpha = mgda_coefficient(first_gradient, second_gradient)
            coefficients = np.array([alpha, 1 - alpha])
        else:
            gradient_norms = np.array([np.linalg.norm(first_gradient), np.linalg.norm(second_gradient)])
            weighted_norms = task_weights * gradient_norms
            relative_rates = np.array([first_loss, second_loss]) / np.maximum(initial_losses, 1e-12)
            relative_rates /= relative_rates.mean()
            targets = weighted_norms.mean() * relative_rates**0.5
            task_weights -= 0.01 * np.sign(weighted_norms - targets) * gradient_norms
            task_weights = np.maximum(task_weights, 1e-3)
            task_weights *= 2.0 / task_weights.sum()
            coefficients = task_weights / task_weights.sum()
        combined = coefficients[0] * first_gradient + coefficients[1] * second_gradient
        weights -= learning_rate * combined
        history.append(
            {
                "method": method,
                "step": step,
                "task_one_loss": first_loss,
                "task_two_loss": second_loss,
                "task_one_weight": float(coefficients[0]),
                "task_two_weight": float(coefficients[1]),
                "combined_gradient_norm": float(np.linalg.norm(combined)),
            }
        )
    first_loss, _ = _regression_loss_gradient(x, first_target, weights)
    second_loss, _ = _regression_loss_gradient(x, second_target, weights)
    return {
        "method": method,
        "task_one_loss": first_loss,
        "task_two_loss": second_loss,
        "mean_loss": 0.5 * (first_loss + second_loss),
        "task_one_weight": history[-1]["task_one_weight"],
        "task_two_weight": history[-1]["task_two_weight"],
        "steps": steps,
        "duration_seconds": perf_counter() - started,
        "shared_parameters": weights.tolist(),
        "history": history,
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def run_experiment(profile: str = "quick", output_dir: Path | None = None) -> ExperimentResult:
    if profile not in {"quick", "full"}:
        raise ValueError("profile must be quick or full")
    total_started = perf_counter()
    output_dir = output_dir or Path("results/d")
    output_dir.mkdir(parents=True, exist_ok=True)

    greedy_selection, greedy_value = greedy_coverage(3)
    exact_selection, exact_value = exhaustive_coverage(3)
    diminishing = verify_diminishing_returns()
    submodular = {
        "candidate_sets": [sorted(group) for group in coverage_sets()],
        "budget": 3,
        "greedy_selection": greedy_selection,
        "greedy_value": greedy_value,
        "exact_selection": exact_selection,
        "exact_value": exact_value,
        "approximation_ratio": greedy_value / exact_value,
        "diminishing_returns": diminishing,
        "guarantee": "The 1-1/e greedy guarantee applies because this objective is normalized, monotone, submodular and constrained only by cardinality.",
    }

    repeats = 3 if profile == "quick" else 8
    iterations = 120_000 if profile == "quick" else 500_000
    scaling = measure_scaling(repeats=repeats, iterations=iterations)
    scheduling = measure_scheduling()
    work_stealing = measure_work_stealing()
    synchronization = measure_synchronization()
    communication = measure_communication()
    locality = measure_locality(repeats=repeats)
    patterns = [data_parallel_demo(), model_parallel_demo(), pipeline_parallel_demo(rounds=35_000 if profile == "quick" else 120_000)]
    interpretation = parallel_interpretation(scaling)

    federated_data = make_federated_data()
    federated_results = [centralized_training(federated_data)]
    for local_steps in (1, 5):
        for rounds in (10, 30):
            federated_results.append(fedavg_training(federated_data, local_steps, rounds))
    federated_history = []
    for index, result in enumerate(federated_results):
        history = result.pop("history")
        label = result["method"] if result["method"] == "centralized" else f"fedavg_l{result['local_steps']}_r{result['rounds']}"
        for row in history:
            federated_history.append({"configuration": label, **row})

    multitask_results = [multitask_training(method) for method in ("equal", "mgda", "gradnorm")]
    multitask_history = []
    for result in multitask_results:
        multitask_history.extend(result.pop("history"))

    summary = {
        "profile": profile,
        "seed": SEED,
        "environment": {
            **environment_metadata(),
            "thread_limits": {
                "OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS", "not set"),
                "OPENBLAS_NUM_THREADS": os.environ.get("OPENBLAS_NUM_THREADS", "not set"),
                "MKL_NUM_THREADS": os.environ.get("MKL_NUM_THREADS", "not set"),
            },
        },
        "submodular": submodular,
        "parallel_interpretation": interpretation,
        "parallel_patterns": patterns,
        "work_stealing": {
            "implementation": "one locked logical deque per worker; owners pop right and idle workers steal left",
            "same_initial_skewed_assignment": True,
            "results": work_stealing,
        },
        "fedavg": {
            "clients": 4,
            "train_samples": len(federated_data["x_train"]),
            "test_samples": len(federated_data["x_test"]),
            "same_split_for_all_methods": True,
            "results": federated_results,
        },
        "multitask": {
            "description": "two conflicting linear-regression tasks sharing one parameter vector",
            "results": multitask_results,
        },
        "execution_labels": {
            "scaling_scheduling_data_model_pipeline": "real local processes with distinct PIDs",
            "synchronization": "real Python threads; shared lock versus local reduction",
            "work_stealing": "real local processes use one logical deque per worker; owners pop right and idle workers steal left",
            "amdahl_gustafson": "analytical interpretation of measured median speedup only",
            "fedavg_multitask": "sequential local simulation of distributed optimization; communication bytes are analytical payload counts, not network measurements",
        },
        "full_profile_status": "DONE" if profile == "full" else "NOT RUN",
        "limitations": [
            "Short local timings are sensitive to OS scheduling, CPU frequency, BLAS behavior and process overhead.",
            "A speedup below one is a valid measured outcome, not corrected or hidden.",
            "The separate deque demonstration implements task stealing with fixed shared-memory buffers and locks; it is educational, not a production lock-free runtime.",
            "FedAvg runs sequential client updates and counts payload bytes; it does not measure a real network.",
            "The two-task linear model is educational and does not establish general MGDA/GradNorm superiority.",
        ],
    }

    _write_csv(output_dir / "parallel_scaling.csv", scaling)
    _write_csv(output_dir / "scheduling.csv", scheduling)
    _write_csv(output_dir / "work_stealing.csv", work_stealing)
    _write_csv(output_dir / "synchronization.csv", synchronization)
    _write_csv(output_dir / "communication.csv", communication)
    _write_csv(output_dir / "locality.csv", locality)
    _write_csv(output_dir / "parallel_patterns.csv", patterns)
    _write_csv(output_dir / "fedavg.csv", federated_results)
    _write_csv(output_dir / "fedavg_history.csv", federated_history)
    _write_csv(output_dir / "multitask.csv", multitask_results)
    _write_csv(output_dir / "multitask_history.csv", multitask_history)
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    worker_medians = []
    for workers in sorted({int(row["workers"]) for row in scaling}):
        worker_medians.append((workers, float(np.median([row["speedup_vs_1_worker_median"] for row in scaling if row["workers"] == workers]))))
    write_bar_svg(
        [str(workers) for workers, _ in worker_medians],
        [speedup for _, speedup in worker_medians],
        output_dir / "speedup.svg",
        "Measured CPU process speedup versus one worker",
    )
    write_bar_svg(
        [result["method"] if result["method"] == "centralized" else f"L{result['local_steps']} R{result['rounds']}" for result in federated_results],
        [result["test_accuracy"] for result in federated_results],
        output_dir / "fedavg_accuracy.svg",
        "Held-out accuracy on identical split",
    )
    return ExperimentResult(
        track="d",
        profile=profile,
        status=RunStatus.DONE,
        method="submodular-parallel-distributed-multitask",
        objective=float(exact_value),
        duration_seconds=perf_counter() - total_started,
        seed=SEED,
        message=f"wrote measured Track D artifacts to {output_dir}",
        metrics={
            "coverage_greedy": greedy_value,
            "coverage_exact": exact_value,
            "max_worker_speedup": interpretation["measured_speedup"],
            "fedavg_configurations": len(federated_results) - 1,
            "multitask_methods": len(multitask_results),
        },
        metadata=environment_metadata(),
    )
