# Prompt 08 — revision

No user follow-up changed scope. Before any kernel edit, the first benchmark smoke showed that the short CPU job completed within zero global ticks on three emulated CPUs. The shared harness was revised to use longer CPU jobs and the final before/after benchmark protocol was changed to identical one-CPU QEMU runs to isolate scheduler policy. The pristine three-hart baseline boot/usertest result was preserved; only final revised benchmark measurements are used for comparison.
