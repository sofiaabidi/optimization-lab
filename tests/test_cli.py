import json

from optlab.cli import main
from optlab.models import ExperimentResult, RunStatus
from optlab.registry import TRACKS


def test_list_reports_every_track(capsys):
    assert main(["list"]) == 0
    output = capsys.readouterr().out
    for key in "ABCDEFGHIJ":
        assert key in output
    assert output.count("DONE") == 10


def test_run_unexecuted_full_profile_is_truthful(capsys):
    assert main(["run", "--track", "j", "--profile", "full"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["track"] == "j"
    assert result["profile"] == "full"
    assert result["status"] == "NOT RUN"
    assert result["duration_seconds"] is None


def test_run_all_has_ten_records(capsys, monkeypatch):
    monkeypatch.setattr(
        "optlab.cli.run_all",
        lambda profile: [
            ExperimentResult(track=track.key, profile=profile, status=RunStatus.NOT_RUN) for track in TRACKS
        ],
    )
    assert main(["run", "--all", "--profile", "full"]) == 0
    records = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert len(records) == 10
    assert {record["track"] for record in records} == set("abcdefghij")
