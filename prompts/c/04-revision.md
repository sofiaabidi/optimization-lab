# Prompt 04 — genuine revision notes

No user follow-up prompt was issued. Two evidence-driven implementation revisions occurred before the final run:

1. The first barren-plateau probe selected a parameter that cancelled exactly under the depth-1 global parity circuit. It was replaced with a non-cancelled parameter position and CZ entanglers; the final tracked sweep measures finite gradients rather than mislabeling a structural zero.
2. The first QAOA quick cap stopped COBYLA at its evaluation limit. A bounded check showed normal trust-region termination near 160 evaluations, so the final quick cap was raised from 100 to 180. The final artifacts report successful termination at 160 evaluations.
