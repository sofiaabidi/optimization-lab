# Prompt 11 — verification

Date: 2026-10-29

Track J's first focused gate and measured quick experiment:

```text
pytest -q tests/test_track_j.py
5 passed in 0.75s

python -m optlab run --track j --profile quick
status DONE; duration 82.4045s
```

The quick profile counted 4,752 maintained pre-J source lines across 18 files, profiled 54 real pytest tests three times, and ran six mutations only in temporary source copies. All six mutations were detected by their scoped real tests. All 12 selected suites passed. Greedy and exact ILP achieved the same weighted objective at every 25/50/75/100% phase budget; at 25%, each selected 51 tests and detected 6/6 injected faults, while the alphabetical prefix selected 10 and detected 0/6. The median complete-suite subprocess wall time was 7.029489 s.

Final focused and repository-wide gates after adding the cross-track validator:

```text
pytest -q tests/test_track_j.py tests/test_artifact_validation.py tests/test_cli.py
9 passed in 0.42s

pytest -q -m 'not slow and not external'
55 passed in 4.76s

python -m optlab.validate_artifacts --output-dir results
A-J: PASS; 49 declared artifact invariants checked

python -m optlab list
exit 0; A-J reported DONE
```

Full profiles were executed into separate directories for A–F and each returned `DONE`. G–J full-profile CLI invocations returned explicit `NOT RUN` statuses: xv6 external scaling, SQLite full scale, quantum breadth/QML, and mutation/scaling respectively. No result was inferred for those deferred profiles. Track D completed and saved all expected artifacts, but the outer execution wrapper did not retain a trustworthy total duration, so no duration is reported.

The final suite has 55 tests because the A–J artifact-consistency test was added after Track J's 54-test timing experiment. The measured experiment was not silently regenerated. Implementation commit: `413d532` (`[AI:Codex] track-j: implement verified CI test selection`). No push was performed.
