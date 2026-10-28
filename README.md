# Optimization Lab

Reproducible workspace for Assignment 8, a ten-track optimization study. Phase 0 provides shared infrastructure only: tracks A–F and H–J are **NOT IMPLEMENTED**; G is **BLOCKED** because its QEMU/RISC-V toolchain is absent. No experiment results are claimed yet.

## Quick start

Python 3.11 is the target. The current WSL2 host has Python 3.14.4, which can run the scaffold, but a Python 3.11 virtual environment is recommended before scientific dependencies are added.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
python -m optlab list
pytest -q -m 'not slow and not external'
```

Run syntax is already stable and reports placeholders honestly:

```bash
python -m optlab run --track a --profile quick
python -m optlab run --all --profile quick
```

`full` is opt-in. It will not silently replace unavailable quantum or xv6 work with simulations. Each implemented track will write raw JSON/CSV beneath `results/<track>/` and link it from the corresponding README.

## Repository map

- `src/optlab/`: result schema, registry, runner, timing, metadata, comparison, I/O, and dependency-free SVG helper.
- `tracks/`: independent A–J experiment documentation and, later, implementations.
- `tests/`: fast infrastructure tests; slow/external work is marked separately.
- `docs/coverage_matrix.md`: provisional requirements and evidence status.
- `prompts/`: evidence workflow and track-specific records; never fabricate missing transcripts.
- `reports/`: technical-report and demonstration templates.

## Environment blockers

- The specific Chapter 6 course deck is missing. The matrix is provisional until it is supplied.
- `qemu-system-riscv64` and a RISC-V cross-compiler are missing, so Track G cannot run.
- Exact Codex model ID is unavailable from the repository/session interface and remains `unknown`.
- No quantum packages are installed during Phase 0.

See [docs/environment.md](docs/environment.md) for the observed Prompt 00 facts and remedies.

## AI disclosure status

The supplied `plan.md` says planning was AI-assisted, but exact planning tool/model metadata must be provided by the student. This Phase 0 scaffold was produced with Codex; the exact model ID is not exposed and is recorded as unknown. Per-track prompt, response, revision, verification, and commit evidence must be captured as work happens. The templates are not evidence by themselves.
