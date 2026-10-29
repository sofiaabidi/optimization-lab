# Prompt 10 — revision

No user follow-up changed scope. The first complete quick run executed the circuits and QML workload but failed while writing `algorithms.csv`: the CSV writer inferred columns from Deutsch–Jozsa, then rejected QFT's `uniform_magnitude_max_error` field. The writer was corrected to use the ordered union of fields across heterogeneous algorithm records, focused tests remained green, and the quick profile was rerun from the start. The failed partial artifact was overwritten; only the successful rerun is reported.

PennyLane 0.45.1 also emitted its known deprecation warning for specifying finite shots on device construction. The finite-shot results were valid, so this is recorded as an API-migration limitation rather than misreported as a failed experiment.
