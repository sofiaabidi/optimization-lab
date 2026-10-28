from __future__ import annotations

from dataclasses import dataclass

from .models import RunStatus


@dataclass(frozen=True)
class Track:
    key: str
    name: str
    path: str
    status: RunStatus
    note: str


TRACKS: tuple[Track, ...] = (
    Track("a", "Continuous optimization", "tracks/a_continuous", RunStatus.DONE, "quick profile implemented; full profile not yet run"),
    Track("b", "Discrete optimization", "tracks/b_discrete", RunStatus.DONE, "quick profile implemented; full profile not yet run"),
    Track("c", "Quantum optimization", "tracks/c_quantum_opt", RunStatus.DONE, "quick simulator profile implemented; full profile not yet run"),
    Track("d", "Parallel and distributed", "tracks/d_parallel_distributed", RunStatus.DONE, "quick profile implemented; full profile not yet run"),
    Track("e", "EV charging", "tracks/e_ev_charging", RunStatus.DONE, "quick profile implemented; full profile not yet run"),
    Track("f", "Compiler optimization", "tracks/f_compiler", RunStatus.NOT_IMPLEMENTED, "Prompt 07"),
    Track(
        "g",
        "xv6-riscv",
        "tracks/g_xv6",
        RunStatus.BLOCKED,
        "QEMU RISC-V and a RISC-V compiler were not found during Prompt 00",
    ),
    Track("h", "DBMS optimization", "tracks/h_dbms", RunStatus.NOT_IMPLEMENTED, "Prompt 09"),
    Track("i", "Quantum algorithms and QML", "tracks/i_quantum_qml", RunStatus.NOT_IMPLEMENTED, "Prompt 10"),
    Track("j", "Software-engineering optimization", "tracks/j_software_engineering", RunStatus.NOT_IMPLEMENTED, "Prompt 11"),
)


def get_track(key: str) -> Track:
    normalized = key.lower()
    for track in TRACKS:
        if track.key == normalized:
            return track
    raise KeyError(key)
