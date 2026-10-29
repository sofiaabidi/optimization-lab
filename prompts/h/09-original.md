# Prompt 09 — original

Source: `prompts.md`, executed on 2026-10-29 with the user's explicit Track H request.

> Implement Track H on real SQLite with deterministic schema, documented row counts and a realistic multi-query workload. Benchmark default/no extra indexes and save query plans via EXPLAIN QUERY PLAN and observed latencies; validate expected query result sets/checksums. Enumerate candidate indexes with measured storage costs and measured workload benefit (including interactions; do not assume additivity blindly). Formulate a storage-budget constrained index selection problem with binary variables and runtime objective, compare greedy choice and DP/ILP subset selection with the SQLite default; evaluate selected combinations on actual DB copies to verify the predictions. Measure repeated query latency, throughput, index storage overhead and index build time separately, warmup method, final plans, same results. Include tests, README, raw data/plots, matrix links; one index alone is insufficient. Run a small real quick profile.

The user additionally required following `plan.md` and repository conventions, realistic documented generation, reproducible artifacts, focused tests, no unrelated refactoring, milestone commits, and reporting only material blockers or deviations.
