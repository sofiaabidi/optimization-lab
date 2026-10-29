# Genuine AI failure log

Three genuine development corrections occurred. They are not upgraded into stronger evidence than was retained. The Track I case has an exact error message; the C and H cases have contemporaneous revision notes but no preserved raw failed artifact/output, so they remain incomplete for any rubric that requires unedited output.

## Track C — structurally zero barren-plateau probe

- Date/tool: 2026-10-29, Codex (exact model ID unavailable), Prompt 04.
- Failure: the first probe chose a parameter that cancelled exactly in the depth-1 global-parity circuit. No raw failed output was retained.
- Correction: use a non-cancelled parameter position and CZ entanglers; bounded tests and the final experiment then measured finite gradients.
- Evidence: `prompts/c/04-revision.md`, `prompts/c/04-verification.md`, and `results/c/barren_plateau_summary.csv`; implementation commit `c3b0e6b`.
- Lesson: a zero gradient can be a circuit symmetry, not evidence of a barren plateau.

## Track H — derived throughput was not measured throughput

- Date/tool: 2026-10-29, Codex (exact model ID unavailable), Prompt 09.
- Failure: the first implementation labeled reciprocal weighted latency as throughput. It also recorded a seed that was not yet an input to row generation. No raw failed artifact was retained.
- Correction: execute three actual 100-query weighted streams, deduplicate identical physical configurations, and make seed 2026 affect generated rows; regenerate final artifacts.
- Evidence: `prompts/h/09-revision.md`, `prompts/h/09-verification.md`, `results/h/throughput_raw.csv`, and implementation commit `2bbfa73`.
- Lesson: derived rates need explicit labels, and reproducibility metadata must affect the data-generation path.

## Track I — heterogeneous CSV serialization failure

- Date/tool: 2026-10-29, Codex (exact model ID unavailable), Prompt 10.
- Triggering prompt: `prompts/i/10-original.md`.
- Unedited retained failure: `ValueError: dict contains fields not in fieldnames: 'uniform_magnitude_max_error'`.
- Root cause/correction: field names were inferred from the first Deutsch–Jozsa row even though later algorithm records have different metrics. The writer now uses the ordered union of all row fields, and a regression test covers heterogeneous rows.
- Re-test/evidence: `prompts/i/10-verification.md`; focused suite `7 passed in 3.10s`; successful artifacts under `results/i/`; implementation commit `ba6d9a5`.
- Lesson: schema construction must inspect all heterogeneous records before opening a strict CSV writer.

Final chat exports/screenshots and student review remain manual evidence tasks. The missing C/H raw failure output must not be reconstructed or fabricated.
