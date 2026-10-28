from __future__ import annotations

from collections.abc import Iterable

from .models import ExperimentResult
from .registry import TRACKS, Track


def run_track(track: Track, profile: str) -> ExperimentResult:
    if track.key == "a":
        from .track_a import run_experiment

        return run_experiment(profile)
    if track.key == "b":
        from .track_b import run_experiment

        return run_experiment(profile)
    if track.key == "c":
        from .track_c import run_experiment

        return run_experiment(profile)
    if track.key == "d":
        from .track_d import run_experiment

        return run_experiment(profile)
    if track.key == "e":
        from .track_e import run_experiment

        return run_experiment(profile)
    if track.key == "f":
        from .track_f import run_experiment

        return run_experiment(profile)
    return ExperimentResult(
        track=track.key,
        profile=profile,
        status=track.status,
        message=track.note,
    )


def run_tracks(tracks: Iterable[Track], profile: str) -> list[ExperimentResult]:
    return [run_track(track, profile) for track in tracks]


def run_all(profile: str) -> list[ExperimentResult]:
    return run_tracks(TRACKS, profile)
