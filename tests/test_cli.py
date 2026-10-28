import json

from optlab.cli import main


def test_list_reports_every_track(capsys):
    assert main(["list"]) == 0
    output = capsys.readouterr().out
    for key in "ABCDEFGHIJ":
        assert key in output
    assert "NOT IMPLEMENTED" in output
    assert "BLOCKED" in output


def test_run_unimplemented_is_truthful(capsys):
    assert main(["run", "--track", "a", "--profile", "quick"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["track"] == "a"
    assert result["profile"] == "quick"
    assert result["status"] == "NOT IMPLEMENTED"
    assert result["duration_seconds"] is None


def test_run_all_has_ten_records(capsys):
    assert main(["run", "--all", "--profile", "full"]) == 0
    records = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert len(records) == 10
    assert {record["track"] for record in records} == set("abcdefghij")
