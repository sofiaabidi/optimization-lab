from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from .registry import TRACKS, get_track
from .runner import run_all, run_track


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="optlab")
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="list tracks and truthful implementation status")
    run = commands.add_parser("run", help="run one track or all tracks")
    target = run.add_mutually_exclusive_group(required=True)
    target.add_argument("--track", choices=[track.key for track in TRACKS])
    target.add_argument("--all", action="store_true")
    run.add_argument("--profile", choices=("quick", "full"), default="quick")
    return root


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "list":
        print("TRACK  STATUS           NAME")
        for track in TRACKS:
            print(f"{track.key.upper():<6} {track.status.value:<16} {track.name}")
        return 0

    results = run_all(args.profile) if args.all else [run_track(get_track(args.track), args.profile)]
    for result in results:
        print(json.dumps(result.to_dict(), sort_keys=True))
    return 0
