# Prompt 00 environment verification

Date: 2026-10-28

Commands actually run are listed in `docs/environment.md`. Observed: Ubuntu 26.04 on WSL2; Python 3.14.4; 12 logical CPUs; 7.7 GiB RAM; clean `main` before Phase 0; no QEMU RISC-V command; no common RISC-V cross-compiler command; no `docs/` course deck. `apt-cache policy` confirmed candidates for the missing xv6 tool packages. No system package was installed.

Exact Codex model ID: unknown (not exposed by the session interface). The final chat response/export must be saved by the student if required; this file is not a substitute for that export.
