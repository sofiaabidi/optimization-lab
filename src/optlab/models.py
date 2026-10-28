from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class RunStatus(str, Enum):
    DONE = "DONE"
    NOT_IMPLEMENTED = "NOT IMPLEMENTED"
    NOT_RUN = "NOT RUN"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class ExperimentResult:
    track: str
    profile: str
    status: RunStatus
    method: str | None = None
    objective: float | None = None
    duration_seconds: float | None = None
    seed: int | None = None
    message: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data
