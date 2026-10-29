# Optimization Lab

Reproducible workspace for Assignment 8, a ten-track optimization study. Tracks A–I have implemented, measured bounded quick profiles; J remains **NOT IMPLEMENTED**. Tracks C and I are simulator-only and make no quantum-advantage claim. Track D distinguishes real local processes from sequential distributed simulation. Track E uses deterministic synthetic campus inputs and preserves infeasible and non-improving cases. Track F implements a small educational compiler and reports when a DP-selected pass order does not generalize. Track G modifies a pinned real xv6-riscv kernel and preserves actual QEMU boot, usertest, benchmark, and patch evidence. Track H measures real SQLite index subsets and reports when greedy matches the exact ILP. Track I reports compiled-Shor and syllabus limits and matched classical QML results. See each track README and the coverage matrix for evidence status.

## Quick start

Python 3.11 is the target. `uv` provisions it without modifying Ubuntu's system Python. VS Code is configured to select `.venv/bin/python`.

```bash
uv python install 3.11
uv venv --python 3.11 .venv
source .venv/bin/activate
uv sync --all-extras --locked
python -m optlab list
pytest -q -m 'not slow and not external'
```

Run syntax is already stable and reports placeholders honestly:

```bash
python -m optlab run --track a --profile quick
python -m optlab run --all --profile quick
```

`full` is opt-in. It will not silently replace unavailable quantum or external-kernel work with simulations. Each implemented track writes raw JSON/CSV beneath `results/<track>/` and links it from the corresponding README.

## Repository map

- `src/optlab/`: result schema, registry, runner, timing, metadata, comparison, I/O, and dependency-free SVG helper.
- `tracks/`: independent A–J experiment documentation and, later, implementations.
- `tests/`: fast infrastructure tests; slow/external work is marked separately.
- `docs/coverage_matrix.md`: provisional requirements and evidence status.
- `prompts/`: evidence workflow and track-specific records; never fabricate missing transcripts.
- `reports/`: technical-report and demonstration templates.

## Current environment constraints

- Track G's QEMU/RISC-V toolchain is installed and its quick profile passed; physical RISC-V hardware and full scaling were not run.
- Exact Codex model ID is unavailable from the repository/session interface and remains `unknown`.
- Coverage named directly by the assignment is preserved. Additional syllabus-specific methods remain transparently uncertain; this is a coverage question, not an environment blocker.

See [docs/environment.md](docs/environment.md) for the observed Prompt 00 facts and remedies.

## AI disclosure status

The supplied `plan.md` says planning was AI-assisted, but exact planning tool/model metadata must be provided by the student. This Phase 0 scaffold was produced with Codex; the exact model ID is not exposed and is recorded as unknown. Per-track prompt, response, revision, verification, and commit evidence must be captured as work happens. The templates are not evidence by themselves.
