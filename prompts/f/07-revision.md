# Prompt 07 — revision

No user follow-up prompt was issued. During review, bytecode execution was changed to run the generated instruction objects directly instead of reconstructing IR inside every timed call. The pass-order training fixture was also separated from held-out programs and adjusted to expose a deterministic propagation-before-folding code-size decision. DP improved the training score but performed worse than the fixed order on held-out instruction count and code size; that non-generalization is preserved in the report.
