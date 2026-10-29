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
    Track("a", "Continuous optimization", "tracks/a_continuous", RunStatus.DONE, "quick and full profiles implemented"),
    Track("b", "Discrete optimization", "tracks/b_discrete", RunStatus.DONE, "quick and full profiles implemented"),
    Track("c", "Quantum optimization", "tracks/c_quantum_opt", RunStatus.DONE, "quick and full simulator profiles implemented"),
    Track("d", "Parallel and distributed", "tracks/d_parallel_distributed", RunStatus.DONE, "quick and full profiles implemented"),
    Track("e", "EV charging", "tracks/e_ev_charging", RunStatus.DONE, "quick and full profiles implemented"),
    Track("f", "Compiler optimization", "tracks/f_compiler", RunStatus.DONE, "quick and full profiles implemented"),
    Track("g", "xv6-riscv", "tracks/g_xv6", RunStatus.DONE, "real QEMU quick profile implemented; full profile not run"),
    Track("h", "DBMS optimization", "tracks/h_dbms", RunStatus.DONE, "real SQLite quick profile implemented; full profile not run"),
    Track("i", "Quantum algorithms and QML", "tracks/i_quantum_qml", RunStatus.DONE, "quick simulator profile implemented; full profile not run"),
    Track("j", "Software-engineering optimization", "tracks/j_software_engineering", RunStatus.DONE, "real pytest selection quick profile implemented; full profile not run"),
)


def get_track(key: str) -> Track:
    normalized = key.lower()
    for track in TRACKS:
        if track.key == normalized:
            return track
    raise KeyError(key)
