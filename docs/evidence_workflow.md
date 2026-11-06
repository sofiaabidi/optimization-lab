# AI evidence workflow

The current records are indexed from [`prompts/README.md`](../prompts/README.md). Planning evidence is under `prompts/planning/`; Tracks A–J use numbered files such as `02-original.md`, `02-revision.md`, `02-verification.md`, and `02-commit.md`.

Only add evidence that actually occurred:

- `*-original.md`: exact user request;
- `*-revision.md`: genuine follow-up or implementation correction, explicitly saying when no user follow-up occurred;
- `*-verification.md`: commands, exit status, concise observed output, and result paths;
- `*-commit.md`: related SHA added only after the commit exists;
- optional sanitized response export/excerpt or reviewed screenshot supplied from the real session.

The repository currently has original, revision, verification, commit, and sanitized prompt/result screenshot records for A–J, plus setup screenshots. Explicit student review notes remain pending. The exact Codex model ID for the A–J sessions remains `unknown` because it was not exposed. A separate bounded two-tool comparison is recorded with its displayed tool/model labels and screenshots. The C/H correction cases still lack retained raw failed output; do not reconstruct those records retrospectively.

Before staging, run `git status --short` and inspect every new file. Never commit credentials, private conversation exports, local environments, or invented metadata. Use `[AI:Codex] ...` for substantially Codex-generated commits and `[MANUAL] ...` for student changes.
