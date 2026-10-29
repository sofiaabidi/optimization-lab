# Technical report preparation template

Status: **final report not yet written**. Tracks A–J have executable evidence; use the [coverage matrix](../docs/coverage_matrix.md), [final handoff](../docs/final_handoff.md), individual [track READMEs](../tracks/), and raw [`results/`](../results/) when preparing the external report. Do not copy estimates or infer unrun full-profile results.

For each A–J section, include:

1. question, objective, decision variables and constraints;
2. dataset/instance, seed, environment and execution mode;
3. baseline and optimization alternatives;
4. independent correctness oracle;
5. a raw-artifact-linked result table or figure with units and repeats;
6. what improved, what did not, and the observed trade-offs;
7. limitations and unsupported claims explicitly excluded;
8. AI-development evidence and relevant commit.

## Section evidence map

| Section | Primary track documentation | Primary result summary |
|---|---|---|
| A — Continuous optimization | [`tracks/a_continuous/README.md`](../tracks/a_continuous/README.md) | [`results/a/summary.json`](../results/a/summary.json) |
| B — Discrete optimization | [`tracks/b_discrete/README.md`](../tracks/b_discrete/README.md) | [`results/b/summary.json`](../results/b/summary.json) |
| C — Quantum optimization | [`tracks/c_quantum_opt/README.md`](../tracks/c_quantum_opt/README.md) | [`results/c/summary.json`](../results/c/summary.json) |
| D — Parallel/distributed | [`tracks/d_parallel_distributed/README.md`](../tracks/d_parallel_distributed/README.md) | [`results/d/summary.json`](../results/d/summary.json) |
| E — EV charging | [`tracks/e_ev_charging/README.md`](../tracks/e_ev_charging/README.md) | [`results/e/summary.json`](../results/e/summary.json) |
| F — Compiler | [`tracks/f_compiler/README.md`](../tracks/f_compiler/README.md) | [`results/f/summary.json`](../results/f/summary.json) |
| G — xv6-riscv | [`tracks/g_xv6/README.md`](../tracks/g_xv6/README.md) | [`results/g/summary.json`](../results/g/summary.json) |
| H — DBMS | [`tracks/h_dbms/README.md`](../tracks/h_dbms/README.md) | [`results/h/summary.json`](../results/h/summary.json) |
| I — Quantum algorithms/QML | [`tracks/i_quantum_qml/README.md`](../tracks/i_quantum_qml/README.md) | [`results/i/summary.json`](../results/i/summary.json) |
| J — Software engineering | [`tracks/j_software_engineering/README.md`](../tracks/j_software_engineering/README.md) | [`results/j/summary.json`](../results/j/summary.json) |

## Cross-track synthesis and final questions

Pending external report preparation. Separate theory from measurement, quick from full profiles, classical/quantum simulation from hardware, and real local parallel/QEMU execution from analytical interpretation. The report must preserve negative results such as C's QAOA gap, E's unchanged peak, F's non-generalizing DP order, G's throughput regression, I's slower simulator execution, and cases where greedy matched exact optimization.
