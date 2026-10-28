# Environment record — Prompt 00

Observed on 2026-10-28. These facts come from the commands below; no packages were installed.

| Item | Observed state | Consequence |
|---|---|---|
| OS | WSL2 Linux, kernel `6.18.54.1-microsoft-standard-WSL2`, x86_64 | Suitable host style for xv6 once tools exist |
| Python | 3.14.4 | Scaffold works; create a Python 3.11 environment for the planned pinned stack |
| Git | `main` tracking `origin/main`, clean before Phase 0 | Repository initialized |
| CPU | Intel i5-10500H, 6 cores / 12 logical CPUs | Adequate for bounded CPU experiments |
| Memory | 7.7 GiB RAM, 2.0 GiB swap | Keep quantum/parallel profiles modest |
| QEMU RISC-V | not found | Track G BLOCKED |
| RISC-V compiler | neither common bare-metal nor Linux cross-compiler found | Track G BLOCKED |
| Chapter 6 deck in `docs/` | absent | Final syllabus coverage cannot be claimed |
| Exact AI model ID | unknown | Must not be guessed |

Commands used:

```bash
uname -a
python3 --version
git status --short --branch
lscpu
free -h
command -v qemu-system-riscv64
command -v riscv64-unknown-elf-gcc
command -v riscv64-linux-gnu-gcc
find docs -maxdepth 2 -type f
```

## Remedies and minimal first run

On Ubuntu/WSL2, first refresh package metadata and verify package names for the installed Ubuntu release. The usual xv6 prerequisites are QEMU system emulation, a RISC-V cross-toolchain, `make`, and `gdb-multiarch`; use the pinned upstream xv6 instructions when Track G begins. Do not mark G unblocked until these commands succeed:

```bash
qemu-system-riscv64 --version
riscv64-unknown-elf-gcc --version  # or the documented supported cross-compiler
```

Install or select Python 3.11, then run:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m optlab list
pytest -q -m 'not slow and not external'
```

Place the authentic Chapter 6 slides/notes under `docs/` (subject to course-sharing rules) or provide a precise taught-method inventory. Then reconcile the provisional coverage matrix before claiming completeness.
