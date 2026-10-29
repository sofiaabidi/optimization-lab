#!/usr/bin/env python3
"""Run one xv6 shell command under QEMU and require a terminal marker."""

from __future__ import annotations

import argparse
import os
import pty
import select
import subprocess
import time
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("command")
    parser.add_argument("marker")
    parser.add_argument("log", type=Path)
    parser.add_argument("--cpus", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()

    master, slave = pty.openpty()
    process = subprocess.Popen(
        ["make", f"CPUS={args.cpus}", "qemu"],
        cwd=args.source,
        stdin=slave,
        stdout=slave,
        stderr=slave,
        close_fds=True,
    )
    os.close(slave)
    deadline = time.monotonic() + args.timeout
    captured = bytearray()
    command_sent = False
    marker_seen = False
    args.log.parent.mkdir(parents=True, exist_ok=True)
    try:
        while time.monotonic() < deadline:
            ready, _, _ = select.select([master], [], [], 1.0)
            if not ready:
                if process.poll() is not None:
                    break
                continue
            chunk = os.read(master, 4096)
            if not chunk:
                break
            captured.extend(chunk)
            text = captured.decode("utf-8", errors="replace")
            if not command_sent and "\n$ " in text:
                os.write(master, (args.command + "\n").encode())
                command_sent = True
            if command_sent and args.marker in text:
                marker_seen = True
                os.write(master, b"\x01x")
                break
        if not marker_seen:
            process.kill()
            raise RuntimeError(f"marker {args.marker!r} not observed before timeout/exit")
        process.wait(timeout=15)
    finally:
        args.log.write_bytes(captured)
        os.close(master)
        if process.poll() is None:
            process.kill()
    print(f"PASS: observed {args.marker!r}; log={args.log}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
