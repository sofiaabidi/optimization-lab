# Prompt 01 verification

Date: 2026-10-28

The first `python3 -m pip install -e '.[dev]'` attempt exited 1 because the WSL system Python is PEP 668 externally managed. The documented remedy was applied by creating `.venv`. The first sandboxed virtual-environment install could not reach the package index; after explicit network approval, the same install succeeded. No large quantum package was installed.

Successful commands and observed results:

```text
.venv/bin/python -m pip install -e '.[dev]'
Successfully installed optimization-lab-0.1.0 and pytest-8.4.2 with its small dependencies

.venv/bin/python -m optlab list
exit 0; A-F and H-J reported NOT IMPLEMENTED; G reported BLOCKED

.venv/bin/python -m optlab run --track a --profile quick
exit 0; JSON status NOT IMPLEMENTED with null duration/objective

.venv/bin/python -m optlab run --all --profile quick
exit 0; ten JSON records with the same truthful statuses

.venv/bin/pytest -q -m 'not slow and not external'
8 passed in 0.05s
```

Uncovered blockers: Python 3.11 is not the active interpreter (3.14.4 was used); the Chapter 6 deck is absent; QEMU RISC-V and a RISC-V cross-compiler are absent; exact Codex model ID and the planning assistant model are unknown. The actual response/export and human-review confirmation still need to be supplied from the chat UI.
