# AI evidence workflow

For each prompt, copy the exact original request into `prompts/<track>/original.md`, then add only evidence that actually occurred:

- `response.md`: sanitized export or meaningful verbatim excerpt supplied from the session;
- `revision.md`: exact follow-up prompt, or `none` only when genuinely none was used;
- `verification.md`: command, timestamp, exit status, concise actual output, and result paths;
- `commit.md`: related commit SHA after the commit exists;
- optional reviewed screenshot/export, with secrets and private context removed.

Before staging, run `git status --short` and inspect every new file. Never commit credentials, private conversation exports, local environments, or invented metadata. Use `[AI:Codex] track-X: ...` for substantially Codex-generated commits and `[MANUAL] ...` for student changes.
