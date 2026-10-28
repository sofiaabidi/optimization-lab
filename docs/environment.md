# Development environment

Validated on 2026-10-28 on Ubuntu 26.04 LTS under WSL2. System Python 3.14.4 was not modified or removed.

## Python and project dependencies

The project uses `uv 0.13.6` and uv-managed CPython 3.11.18. VS Code selects `.venv/bin/python` through `.vscode/settings.json`. `uv.lock` records the complete resolution; direct project dependencies are intentionally split by use:

| Group | Direct pinned packages | Planned use |
|---|---|---|
| `dev` | pytest 8.4.2 | Fast tests |
| `scientific` | NumPy 2.3.5, SciPy 1.16.3, Matplotlib 3.10.7 | A/B/D/E/H/J numerics, SciPy LP/MILP, plots |
| `ml` | PyTorch 2.10.0+cpu | A backprop and D/I learning experiments |
| `quantum` | PennyLane 0.45.1 | C/I circuits, QAOA/VQE/QML and simulator noise |
| `database` | none | H uses Python's standard-library SQLite 3.53.1 |

PyTorch is resolved from its CPU-only wheel index; CUDA is unavailable and was not downloaded. Qiskit, separate ILP solvers, GPU packages, and database drivers are deferred because the planned implementations do not currently require them.

Recreate the verified environment:

```bash
uv python install 3.11
uv venv --python 3.11 --clear .venv
uv sync --all-extras --locked
source .venv/bin/activate
```

If `uv` is not yet installed, use the pinned official standalone installer without changing shell startup files:

```bash
curl -LsSf https://astral.sh/uv/0.13.6/install.sh | env UV_NO_MODIFY_PATH=1 sh
export PATH="$HOME/.local/bin:$PATH"
```

## Ubuntu system tools

Ubuntu 26.04 repository availability was inspected with `apt-cache policy` before attempting installation.

| Tool/package | Repository candidate or observed version | Status |
|---|---|---|
| `make` | 4.4.1-3 / GNU Make 4.4.1 | PASS — installed |
| `qemu-system-misc` | 1:10.2.1+ds-1ubuntu3.3 | FAIL — sudo authentication required; not installed |
| `gcc-riscv64-unknown-elf` | 14.2.0+19 | FAIL — sudo authentication required; not installed |
| `binutils-riscv64-unknown-elf` | 2.45.50.20251209-1ubuntu1+7build1 | FAIL — sudo authentication required; not installed |
| `gdb-multiarch` | 17.1-2ubuntu1 | FAIL — sudo authentication required; not installed |

Run this once in an interactive WSL terminal:

```bash
sudo apt update
sudo apt install qemu-system-misc gcc-riscv64-unknown-elf binutils-riscv64-unknown-elf gdb-multiarch
```

Then verify:

```bash
qemu-system-riscv64 --version
riscv64-unknown-elf-gcc --version
gdb-multiarch --version
```

Tool installation alone does not validate Track G. A pinned upstream xv6 checkout must still build, boot in QEMU, and run `usertests` during Prompt 08. Until the packages above are installed, G remains `BLOCKED`; the xv6 boot gate is `DEFERRED`.

## Validation record

| Check | Result | Observed evidence |
|---|---|---|
| Python version | PASS | `.venv/bin/python` is CPython 3.11.18 |
| Editable package and CLI | PASS | `optlab 0.1.0`; `python -m optlab list` exits 0 with truthful scaffold statuses |
| Fast pytest suite | PASS | 8 passed in 0.06 s |
| Scientific imports and ILP | PASS | NumPy 2.3.5; SciPy 1.16.3; Matplotlib 3.10.7; one-variable integer MILP optimum verified as 1.0 |
| ML/autograd | PASS | PyTorch 2.10.0+cpu; gradient of `x²` at 3 verified as 6; CUDA false |
| Quantum simulator | PASS | PennyLane 0.45.1 `default.qubit`; `RY(π)` Pauli-Z expectation verified as -1.0 |
| Database | PASS | stdlib SQLite 3.53.1; in-memory create/insert/aggregate verified |
| GNU Make | PASS | 4.4.1 |
| QEMU RISC-V executable | FAIL | `qemu-system-riscv64`: command not found |
| RISC-V compiler executable | FAIL | `riscv64-unknown-elf-gcc`: command not found |
| GDB multiarch executable | FAIL | `gdb-multiarch`: command not found |
| xv6 build/boot/usertests | DEFERRED | belongs to Track G after tool installation and upstream pinning |

The scientific and quantum smoke commands set `MPLCONFIGDIR=/tmp/optlab-matplotlib` because the automated sandbox cannot write the user's normal Matplotlib cache directory. This is a sandbox constraint, not a dependency failure.

## Coverage note

Every algorithm and requirement named by the assignment remains in `docs/coverage_matrix.md`. Additional syllabus-specific coverage is transparently uncertain until an authoritative taught-method inventory is supplied; this is not an environment blocker.
