# Optimization Lab — Execution Plan

> Assignment 8: **Optimize Anything — 14-Day Vibe-Coding Challenge**  
> Status: planning artifact, **not an assertion that experiments were run**.  
> Companion: [`prompts.md`](prompts.md). Read this file first; use the numbered prompts in order.

## 1. North star and non-negotiables

Build **one reproducible, public GitHub repository containing ten focused experiments (A–J)**, each with a formulation, baseline, real execution, correctness evidence, comparison, limitations, and AI-assisted development trace. The goal is rigorous evidence, **not a dashboard or giant application**.

**Definition of success:** another student can clone the repository, install documented dependencies, reproduce the feasible experiments, understand which optional infrastructure is required, inspect raw results, and explain the design in a viva. An optimization that performs worse is acceptable **if accurately measured and explained**.

- Complete **all ten compulsory tracks** and every Chapter 6 topic **actually taught**. The supplied assignment names many techniques, and refers to additional course-specific methods as “where covered.” The *actual chapter slides/notes must be reconciled* before claiming complete coverage. A provisional detailed list is in §5.
- Each track must explicitly record: objective; decision variables; constraints/assumptions; dataset, seed, hardware/software; baseline; alternatives; correctness oracle; measured results; trade-offs; code/results paths.
- Do **not** generate fake measurements, screenshots, failure stories, model IDs, dates, commits or tool comparisons. Mark `NOT RUN`/`BLOCKED` with the reason if the environment cannot run something. A blocked required track is **not complete**.
- For stochastic methods, repeat runs where feasible; report spread, not just best results. Separate objective quality from time; label theory, classical simulation, noisy simulation and actual hardware honestly.
- Preserve original benchmark inputs and program semantics. Measure baseline and optimized versions on identical workloads and stated resources; save data in machine-readable form.
- Implement every track with AI assistance **and** keep authentic prompt/response/revision/verification/commit records. Keep the exact transcript/export where practical. Log manual corrections separately.
- Prioritize few meaningful gates: one focused verification after each track or fragile subsystem, then one final integration/reproducibility audit. **xv6 requires additional smoke tests after each kernel change** for safety.

## 2. Decisions that keep the scope reasonable

| Decision | Choice | Rationale |
|---|---|---|
| Organization | Python monorepo, independent `tracks/a...j` modules | Shared utilities; easy single CLI and pytest |
| Primary Python | Python 3.11, pinned dependency groups | Broad support for scientific and quantum tooling; avoid forcing all dependencies for every experiment |
| Data | Deterministic synthetic datasets and documented seeds | Replication without private data |
| Results | JSON/CSV raw data + small PNG/SVG plots + Markdown interpretations | Evidence is auditable, not just screenshots |
| Continuous | NumPy/SciPy, PyTorch for small backprop test | Manual derivations where educational; use libraries where legitimate |
| Integer methods | SciPy `milp` or an explicitly pinned open-source ILP backend | No paid solver requirement |
| Quantum | PennyLane and/or Qiskit simulators; optional simulator noise | No quantum-hardware access assumed |
| DBMS | SQLite with `EXPLAIN QUERY PLAN`, reproducible fixed data | Easy setup; explicit optimizer comparisons still necessary |
| Compiler | Tiny language → AST → IR → interpreter/code generator | Easier to verify semantics than full LLVM toolchain |
| OS | **Pinned upstream xv6-riscv** in `external/` (ignored) + tracked clean patches, workloads, scripts and provenance | Real xv6 modifications, not a mock scheduler |
| Main case study E | **Campus EV charging-slot allocation** with electricity price, peak capacity and deadlines | Distinct from fixed F–J domains; transparent optimization and data |
| Software engineering J | **Prioritization/selection of tests in this repo (once ≥1,000 LOC)** under a CI time budget, with real timed runs and fault-detection evidence | Real codebase, optimization objective and measurable cost |
| UI | None required | Focus effort on research quality, tests, plots and documentation |

### Case E formulation (planned)

A campus has EVs with required energy, arrival/departure slots and per-slot charging-power limits. The charger facility has a total capacity per slot, and electricity prices vary by slot. Let `x[v,t]` = energy assigned to vehicle `v` in time slot `t`. Minimize `sum_t price[t] * sum_v x[v,t]` (optionally report peak-load penalty as a separate sensitivity experiment). Constraints: `0 ≤ x[v,t] ≤ charger_limit[v] * slot_duration` when present; `x[v,t] = 0` outside its parking window; `sum_v x[v,t] ≤ facility_limit[t] * slot_duration`; each vehicle receives its required energy by departure. Create **feasible** and **infeasible** fixed instances; explicitly detect infeasibility.

Baseline: deterministic first-available/first-come charging (feasibility-aware). Optimizers: greedy cheapest-feasible-slot heuristic **versus exact LP/ILP** (continuous energy LP is valid; discrete whole-slot charging can use ILP). Compare total electricity cost, unmet demand, peak usage, runtime, and behavior as fleet size grows. Do not claim the baseline always returns a feasible solution; represent failure explicitly.

### Cross-track reuse, with boundaries

- **B → C:** one *identical*, tiny weighted Max-Cut instance, enumerated classical optimum, QUBO penalty/Ising mapping, QAOA classical-simulator comparisons. In B also use a separate constrained selection/knapsack task to exercise ILP, branch-and-bound and dynamic programming.
- **A → C/I:** reuse optimizer interfaces/plotting but distinguish backprop from optimizer updates and simulated circuit gradients.
- **D → J:** reuse timing infrastructure only; D studies parallel algorithms and distributed learning, J studies real test-suite selection/prioritization.
- **E ↔ B:** reuse formulation helpers if useful, not the main experimental conclusion. E must be a distinct end-to-end case study with ≥2 alternatives.
- **C ≠ I:** C is variational *optimization mechanics* and noise/plateau experiments; I is the named *quantum algorithms*, QML comparison and query/gate complexity.

## 3. Repository blueprint

```text
optimization-lab/
├── README.md                     # Full setup, quickstart, actual tool register
├── plan.md                       # This roadmap and completion map
├── prompts.md                    # Copy-paste Codex prompts
├── pyproject.toml                # Minimal base + optional dependency groups
├── .gitignore
├── .github/workflows/ci.yml      # Fast CPU-only checks (no xv6/large quantum jobs)
├── src/optlab/                   # Shared config, seed, result schema, plots, CLI
├── tracks/
│   ├── a_continuous/
│   ├── b_discrete/
│   ├── c_quantum_opt/
│   ├── d_parallel_distributed/
│   ├── e_ev_charging/
│   ├── f_compiler/
│   ├── g_xv6/
│   ├── h_dbms/
│   ├── i_quantum_qml/
│   └── j_software_engineering/
├── tests/                        # Small unit & correctness tests, tagged slow tests
├── benchmarks/                   # Shared workload definitions and benchmark runner
├── results/                      # Raw CSV/JSON, metadata, plots, brief interpretations
├── reports/
│   ├── technical_report.md       # A–J sections plus cross-track synthesis
│   └── demo.md                   # Short reproducible demonstration script
├── docs/
│   ├── coverage_matrix.md        # Every named Chapter 6 method → executable evidence
│   ├── environment.md            # Versions, CPU/OS, constraints, QEMU/Qiskit, caveats
│   ├── tool_comparison.md         # Actual 2-tool same-task experiment
│   └── failure_log.md            # ≥3 genuine AI-error incidents, not staged
├── prompts/                      # a/ ... j/ plus planning/; actual prompt logs & captures
└── external/                     # gitignored pinned xv6 checkout/venvs/build output
```

Keep experiments, tests and writeups in each track folder. No duplicated framework, unnecessary Docker/Kubernetes or frontend. Large generated data and xv6 build binaries should not enter Git.

## 4. Execution contract: what every finished track must output

Each track must have:

1. `README.md` — question, formulation, method choice, dataset assumptions, commands, results and limitations.
2. Runnable entrypoint or script, deterministic seed where appropriate; baseline and at least one optimization.
3. A **correctness oracle** independent of the optimized method (analytic optimum, enumeration, reference semantics, checksums, equivalent query results, or invariant testing).
4. Reproducible result files (recommended `results/<track>/raw.csv`, `summary.json`, figure). Every reported number derives from a measured run and includes units and environment metadata; repeats where appropriate.
5. A verification note and authentic AI log under `prompts/<track>/` with source tool/model, timestamps, original prompt, actual response excerpt or transcript, revision, commit SHA/link and human review. Do not claim logs exist when they do not.
6. Entry in `docs/coverage_matrix.md` mapping every relevant taught method to the exact code function, test, output and status (`DONE`, `NOT RUN`, `BLOCKED`, `NOT TAUGHT—confirmed`).

## 5. Specific track acceptance criteria / provisional coverage

The following is a **minimum from the supplied assignment**; expand based on real Chapter 6 teaching materials. A line is done only if code/demo **and observed evidence** are linked.

### A — Continuous optimization / foundations

- [ ] Small ML loss + regularizer showing parameters, objective, gradient and backward pass; illustrate continuous vs discrete optimization, convex vs nonconvex, local/global minima and saddle point with actual numerical examples.
- [ ] Comparable GD, SGD, mini-batch SGD, Momentum, NAG, AdaGrad, RMSProp, Adam, Newton, Gauss–Newton experiments; use suitable objectives where algorithms make sense.
- [ ] Backpropagation separately verified against finite differences or autograd. Demonstrate at least one Fisher/diagonal Hessian/Hessian-vector-product curvature approximation, stating what was used.
- [ ] Convergence on convex, strongly convex and nonconvex objectives; sensitivity to learning rate, batch size/noise, optimizer settings; objective trajectories, runtime and failure behavior.

### B — Discrete optimization

- [ ] One constrained selection/knapsack benchmark solved using greedy, ILP, branch-and-bound and DP (where taught); feasibility and optimality checked with enumeration on small cases.
- [ ] One small weighted Max-Cut instance: adjacency/weights, classical exhaustive optimum, QUBO matrix, Ising change of variables (`x=(1-z)/2`), energies verified exhaustively.
- [ ] Separate example of **penalty terms for constraints** (e.g., cardinality-constrained binary selection), show penalty strength and feasible/infeasible behavior; not all Max-Cut formulations have constraints.
- [ ] Feature selection or other combinatorial example **if present in course**; record choice and Chapter 6 alignment.

### C — Quantum optimization

- [ ] Same Max-Cut instance as B; actual QAOA variational circuit and objective, with finite-shot experiments and classical exhaustive comparison.
- [ ] VQE on a small stated Hamiltonian; demonstrate PQC/QNN optimization and at least one hybrid quantum-classical training loop.
- [ ] Parameter-shift, SPSA, and quantum natural gradient (document the metric approximation used); compare on a controlled problem, separating circuit evaluations from wall time.
- [ ] Finite-shot cost, plausible simulator noise, barren-plateau gradient-variance-vs-depth/qubit demonstration, and QUBO-to-annealer embedding limitations explained with a concrete small example.

### D — Submodular / parallel / distributed

- [ ] Coverage/facility-selection submodular objective: diminishing-returns check on sampled/exhaustive small subsets, greedy selection against exact small optimum, guarantee only when conditions hold.
- [ ] Load balancing, makespan, scheduling, work stealing, locality, synchronization and communication overhead studied with actual CPU/process measurements; report speedup and efficiency across worker counts. Some simulations may *illustrate* strategies, but a simulated speedup must **not** be called measured parallel speedup.
- [ ] Demonstrate data, model and pipeline parallelism on small educational tasks; identify what actually ran simultaneously vs analytical/simulated parts.
- [ ] Use measured outcomes to interpret Amdahl/Gustafson, not to claim unmeasured scaling.
- [ ] FedAvg versus centralized training; vary local steps/rounds; MGDA and GradNorm versus equal task weights on a genuine two-task setup. Record accuracy/loss/communication/compute tradeoffs.

### E — Campus EV charging allocation

- [ ] Plain-language process, baseline inefficiency, explicit variables, cost objective, time/charging/facility constraints, feasible+infeasible deterministic cases.
- [ ] Baseline vs two **different** optimized methods (greedy cheapest slot and LP/ILP); fair comparisons and correctness/feasibility tests.
- [ ] Strategy selection table (variable type, instance size, exact vs heuristic, hardware, parallelism); cost, latency, peak load and unmet energy; scaling and sensitivity analysis, non-improvement cases.

### F — Compiler optimization

- [ ] Tiny usable compiler (lexer, parser, AST/IR, code generator or interpreter); tests establish source/IR/code behavioral equivalence.
- [ ] **Four** optimization passes for full credit (at minimum two): constant folding, constant propagation, dead-code elimination, common subexpression elimination (choose only if safe for defined language semantics).
- [ ] Make **pass ordering**, register allocation or instruction scheduling an explicit optimization problem, solve using greedy/DP/ILP, compare to naïve order.
- [ ] Report instruction count, runtime, generated code size, compile time, and semantic equivalence across representative programs; address measurement noise and pathological examples.

### G — Real xv6-riscv modification

- [ ] Select and pin exact upstream xv6-riscv commit and required RISC-V QEMU toolchain; record provenance, licenses, reproducible setup and patch application.
- [ ] Implement **one tested kernel feature minimum** (recommend priority/lottery scheduler with accounting); **second distinct feature for full credit** (e.g. scheduler-statistics syscall or another bona fide kernel feature). Clearly explain why the second constitutes a feature.
- [ ] Baseline and modified kernel built and booted in QEMU, with same **≥3 workloads** (CPU-bound, mixed yield/I/O, fairness/contention). Measure response/turnaround/throughput/fairness with user-space benchmark programs and reproducible scripts.
- [ ] Run xv6 `usertests` and relevant smoke tests after each kernel change; preserve build/run logs and **tracked actual patch/diff**. No invented benchmark data; cannot count a Python scheduler simulation as xv6.
- [ ] If QEMU/toolchain unavailable: document exact blocker and command needed, leave status BLOCKED, never mark complete.

### H — DBMS optimization

- [ ] Documented seeded SQLite dataset large enough to make plan differences meaningful; fixed schema, queries, row counts, transaction settings, warmup and measurement process.
- [ ] **Optimize an actual decision** (recommend index-set selection under storage budget) with variables, objective (weighted query cost/latency), constraints, **greedy vs exact knapsack/ILP/DP** and SQLite default/no-added-index baseline. Adding one index alone is inadequate.
- [ ] Save `EXPLAIN QUERY PLAN` before/after, repeated latencies, throughput, total index-storage overhead; assert identical query result sets and sensible database query semantics.

### I — Named quantum algorithms and QML comparison

- [ ] Simulator circuits for **every quantum algorithm actually taught**; provisional minimum: Deutsch–Jozsa, Bernstein–Vazirani, Grover, QFT, Quantum Phase Estimation, Shor (small educational compiled/example factoring demonstration clearly scoped), quantum annealing (classical/annealing simulator with limitation), plus QAOA/VQE cross-reference in C.
- [ ] Hand-build at least **two** circuits (not library black boxes) and check outputs on analytically known instances.
- [ ] Quantum kernels and variational classifier/QNN compared with fair classical baselines on identical train/test splits; accuracy, training time, parameters, circuit-evaluation counts.
- [ ] Grover versus classical linear search: query/gate counts **and** measured wall clock; make theoretical versus simulated distinction. Include at least one noise-model experiment or real hardware **where access allows**; discuss data loading, noise, simulation overhead and barren plateaus; compare honestly to D.

### J — Software-engineering optimization

- [ ] Confirm nontrivial repository codebase has ≥1,000 source LOC when J starts (exclude vendored/dependency/generated code); profile actual suite/test timings and documented failure/fault detection.
- [ ] Define test selection/prioritization variables, fault/feature coverage objective and CI runtime budget, costs and correctness constraints.
- [ ] Baseline alphabetical or full-suite order vs a named Chapter 6 method (greedy maximum coverage or DP/knapsack) with real timed executions. Measure detection under a fixed time budget, overhead and tradeoffs, not just theoretical scores.
- [ ] Use a **safe, reproducible fault set** such as pre-existing real defects or clearly labeled injected mutations; do not fabricate real-world failures or edit repository tests to misrepresent performance. Preserve normal suite and assess maintainability/readability.

## 6. AI-assisted work and audit trail

The planning document and prompt template were prepared with AI. **Record the actual tool and model/version used, date and purpose** rather than guessing. Codex must not invent its own response logs/identifiers. Capture its conversation exports/screenshots in a safe sanitized form. Sample tracked structure:

```text
prompts/planning/00-planning.md
prompts/a/01-original.md
prompts/a/01-response-excerpt.md
prompts/a/01-revision.md
prompts/a/01-verification.md
prompts/a/01-chat-export-or-screenshot.*
```

Each experiment: record original prompt (copied from `prompts.md`), a meaningful actual response/excerpt, revision **if actually made**, exact related commit hash, test command and measured results. No invented revisions; note `none needed` if so, but assignment calls for prompt revisions and significant AI corrections across work. Use `[AI:Codex] track-a: ...` for AI-written changes; `[MANUAL] ...` for manual corrections. Avoid committing secrets, tokens, local user paths, large datasets or private conversations.

**Three genuine failure cases:** log triggering prompt and generated faulty code/change, actual failure evidence, correction, re-test and lesson. Do not intentionally sabotage output or invent bugs to fill the quota; keep looking for genuine issues and seek instructor guidance if fewer than three arise.

**Two-tool comparison:** select a bounded task (e.g. implementing a small exact QUBO-to-Ising energy verifier), send *the same requirements* independently to Codex and another real AI tool, then run the same predefined tests. Log actual model/version, transcript, elapsed observed time or `not measured`, iterations, correctness, false claims and selected solution. The second tool's code need not be merged. This assignment already involves ChatGPT for planning; disclose it.

## 7. Execution order and meaningful gates

| Phase | Prompts | Deliverable | Acceptance gate |
|---|---|---|---|
| 0. Bootstrap | 00–01 | Git repository, reproducible skeleton, common runners, tool/coverage templates | `pytest -q` and CLI smoke work |
| 1. Mathematical foundations | 02–03 | A, B | analytic/exhaustive oracles and raw results |
| 2. Quantum optimization | 04 | C | same B Max-Cut energies; runs labelled simulator |
| 3. Parallel and federated | 05 | D | actual speedup measurement and correct distributed baselines |
| 4. Applied study | 06 | E | feasible schedules, fair cost comparisons |
| 5. Systems | 07–09 | F, G, H | compiler semantics; xv6 boot/usertests; DB result equality |
| 6. Quantum breadth, engineering | 10–11 | I, J | known circuits and real J codebase evidence |
| 7. Research audit | 12–14 | Chapter 6 coverage, AI logs, report/demo, audit | no unsupported completion claims |

**14-day pacing suggestion:** days 1–3 bootstrap, environments and E baseline; days 4–7 A–D and F–H first passes; days 8–11 E, I, J and detailed benchmarks; days 12–14 reruns, source-to-report reconciliation, AI logs, report and demonstration. Sequencing in `prompts.md` is optimized for dependencies rather than literal calendar order. The xv6 environment should be checked **early** in Phase 0; do not leave QEMU installation until Phase 5.

At each gate, fix **real** failing tests and reproducibility blockers; no endless style audits or speculative rewrites. Codex should report changed files, actual commands/results, skipped tests, blockers and next prompt. Don't repeatedly run full expensive quantum suites on every edit.

## 8. Setup requirements and run policy

- Recommended development environment: **VS Code + Codex extension, Git, Python 3.11, WSL2 Ubuntu (on Windows)**. xv6-riscv needs QEMU system RISC-V and a RISC-V cross-compiler; confirm package names/commands against the pinned xv6 upstream instructions for the actual distro. Native Windows terminal should not be assumed adequate for xv6.
- Runtime packages are installed in separate optional extras (`base`, `ml`, `quantum`, `database`, `dev`) with **locked versions after compatibility is proven**, not one huge default install. For quantum experiments use a separate virtual environment if dependencies conflict.
- `pytest` fast suite excludes expensive experiments/QEMU; manual `python -m optlab run --track <id>` (finalize CLI syntax in Prompt 01) runs a bounded track. `python -m optlab run --all --profile quick|full` should run explicit feasible profiles and record SKIPPED/BLOCKED truthfully.
- Track G baseline and patched copies must use same upstream base commit, compilation flags, QEMU settings and user-level workloads. Track H should not include database build/initialization in query latency; record separate setup time.
- Do not claim CI validates external QEMU or quantum workloads if CI runs only fast unit tests. CI is supporting evidence, **not** a substitute for local full experiments.

## 9. Final acceptance checklist

- [ ] Public GitHub URL, README/setup dependencies and actual execution commands.
- [ ] All ten tracks have runnable code, baseline, correctness tests and honest measured results.
- [ ] Chapter 6 teaching slides reconciled against `docs/coverage_matrix.md`; no unexplained gaps.
- [ ] Compiler **four** passes for full-credit target; optimized output preserves semantics.
- [ ] xv6 genuine patch, three workloads, boot and `usertests`, second feature if aiming for full credit.
- [ ] DBMS optimizer selection formulated and compared with SQLite baseline; query equality proven.
- [ ] Quantum algorithms/QML comparisons, hand-built circuits, simulator/hardware/noise status disclosed.
- [ ] Stochastic repeats, variance, runtime/quality/overhead and reproducibility metadata.
- [ ] README AI-tool register, per-track prompt logs and genuine revisions, attributable commits, three *genuine* documented AI failure/fix cases, actual two-tool comparison.
- [ ] `reports/technical_report.md` covers all A–J tracks and final ten assignment questions; short demonstration script works.
- [ ] No secrets, personally identifiable records, fake data/results, missing licenses, or unsupported success claims.
- [ ] Student can explain and change important code live without AI.

### Open decisions before final full-credit claim

1. **Exact Chapter 6 slide deck / taught syllabus:** the supplied assignment is broad and some items explicitly depend on what was taught. Obtain the real chapter material and adjust the coverage map; do not quietly assume the provisional list is exhaustive.
2. **Available OS/toolchain:** record whether WSL/QEMU/RISC-V gcc and sufficient CPU/RAM are available; if not, set up xv6 environment before progressing far.
3. **Quantum hardware:** not assumed; permitted simulator/noise-model route must be labelled honestly.
4. **AI logging:** enable/export real Codex conversations and keep a second-tool comparison record as the project proceeds.
