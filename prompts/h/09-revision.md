# Prompt 09 — revision

No user follow-up changed scope. Three genuine implementation corrections were made before final evidence:

1. The first version reported throughput as the reciprocal of weighted measured latency. It was revised to execute three actual 100-query weighted streams and retain their wall times and rates separately.
2. When greedy and exact ILP selected the same physical index set, measuring it twice produced different rates from host noise. The final runner deduplicates identical configurations and reports the same real measurement for both methods.
3. The generator was deterministic but initially recorded a seed without using it in row construction. Seed 2026 is now an actual input to the deterministic department, student, course, term and grade formulas; final artifacts were regenerated afterward.

Latency repeats were increased from three to five after the preliminary run exposed timing variability. Only the final seeded five-repeat artifacts are reported.
