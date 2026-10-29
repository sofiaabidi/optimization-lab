# Prompt 11 — revision

No user follow-up changed scope and the first real Track J experiment completed successfully. Before execution, two safety/reporting details were tightened: pre-J LOC explicitly excludes both Track J additions, and all stored log paths are repository-relative rather than local absolute paths. Mutations run only in disposable copied source trees; no repository source or test is changed by a mutation run.

The experiment distinguishes measured pytest phase budgets from actual subprocess wall time. This correction is essential because collection/import startup dominates very small selected suites; the optimization does not claim the phase budget equals end-to-end CI time.
