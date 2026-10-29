"""Run pytest while recording precise per-node setup/call/teardown durations."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Sequence

import pytest


class TimingPlugin:
    def __init__(self, output: Path) -> None:
        self.output = output
        self.durations: dict[str, dict[str, float]] = defaultdict(dict)
        self.nodeids: list[str] = []

    def pytest_collection_finish(self, session: pytest.Session) -> None:
        self.nodeids = [item.nodeid for item in session.items]

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        if report.when in {"setup", "call", "teardown"}:
            self.durations[report.nodeid][report.when] = float(report.duration)

    def pytest_sessionfinish(self, session: pytest.Session) -> None:
        rows: list[dict[str, Any]] = []
        for nodeid in self.nodeids:
            phases = self.durations.get(nodeid, {})
            rows.append(
                {
                    "nodeid": nodeid,
                    "setup_seconds": phases.get("setup", 0.0),
                    "call_seconds": phases.get("call", 0.0),
                    "teardown_seconds": phases.get("teardown", 0.0),
                    "total_seconds": sum(phases.values()),
                }
            )
        self.output.parent.mkdir(parents=True, exist_ok=True)
        self.output.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(arguments: Sequence[str] | None = None) -> int:
    values = list(arguments if arguments is not None else sys.argv[1:])
    if not values:
        raise SystemExit("usage: python -m optlab.pytest_profile OUTPUT.json [pytest arguments...]")
    output = Path(values.pop(0))
    plugin = TimingPlugin(output)
    return int(pytest.main(values, plugins=[plugin]))


if __name__ == "__main__":
    raise SystemExit(main())
