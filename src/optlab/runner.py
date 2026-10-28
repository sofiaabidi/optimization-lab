from __future__ import annotations

from collections.abc import Iterable

from .models import ExperimentResult
from .registry import TRACKS, Track


def run_track(track: Track, profile: str) -> ExperimentResult:
    """Return an honest placeholder until a track registers an implementation."""
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
