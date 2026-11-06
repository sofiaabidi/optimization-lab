# Prompt evidence

These directories contain the actual prompt, revision, verification, and commit records produced during implementation. See the [evidence workflow](../docs/evidence_workflow.md) before adding anything; missing exports or review must remain missing rather than being recreated.

| Scope | Records |
|---|---|
| Planning and environment | [`planning/`](planning/) |
| Setup screenshots | [`setup/`](setup/) |
| Track A — continuous | [`a/`](a/) |
| Track B — discrete | [`b/`](b/) |
| Track C — quantum optimization | [`c/`](c/) |
| Track D — parallel/distributed | [`d/`](d/) |
| Track E — EV charging | [`e/`](e/) |
| Track F — compiler | [`f/`](f/) |
| Track G — xv6 | [`g/`](g/) |
| Track H — SQLite | [`h/`](h/) |
| Track I — quantum algorithms/QML | [`i/`](i/) |
| Track J — test selection | [`j/`](j/) |
| Independent tool comparison | [`tool_comparison/`](tool_comparison/) |

Sanitized prompt/result screenshots are now tracked for setup and Tracks A–J, and independent Codex/Antigravity comparison screenshots are under `tool_comparison/`. Still requiring user-supplied evidence: explicit student review and complete raw before/failure evidence for the C and H correction cases.
