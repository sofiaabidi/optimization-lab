from __future__ import annotations

import platform
import random
import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from time import perf_counter
from typing import TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class Comparison:
    baseline: float
    method: float
    absolute_change: float
    relative_change: float | None


def compare(baseline: float, method: float) -> Comparison:
    return Comparison(
        baseline=baseline,
        method=method,
        absolute_change=method - baseline,
        relative_change=None if baseline == 0 else (method - baseline) / abs(baseline),
    )


def seeded_random(seed: int) -> random.Random:
    return random.Random(seed)


def timed(function: Callable[..., T], *args: object, **kwargs: object) -> tuple[T, float]:
    started = perf_counter()
    value = function(*args, **kwargs)
    return value, perf_counter() - started


def repeat(function: Callable[[], T], repeats: int) -> list[tuple[T, float]]:
    if repeats < 1:
        raise ValueError("repeats must be positive")
    return [timed(function) for _ in range(repeats)]


def environment_metadata() -> dict[str, str]:
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "processor": platform.processor() or "unknown",
    }


def mean(values: Iterable[float]) -> float:
    materialized = list(values)
    if not materialized:
        raise ValueError("at least one value is required")
    return sum(materialized) / len(materialized)
