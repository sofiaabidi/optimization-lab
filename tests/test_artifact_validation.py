from optlab.validate_artifacts import validate_artifacts
from optlab.track_j import repository_root


def test_measured_artifacts_are_consistent_across_tracks_a_to_j():
    rows = validate_artifacts(repository_root())
    assert [row.track for row in rows] == list("ABCDEFGHIJ")
    assert all(row.status == "PASS" for row in rows), rows
