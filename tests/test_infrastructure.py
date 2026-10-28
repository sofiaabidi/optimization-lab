import json

import pytest

from optlab.experiment import compare, mean, repeat, seeded_random
from optlab.io import write_result, write_rows
from optlab.models import ExperimentResult, RunStatus
from optlab.plotting import write_bar_svg


def test_seeded_random_is_reproducible():
    assert seeded_random(7).random() == seeded_random(7).random()


def test_comparison_and_mean():
    result = compare(10.0, 8.0)
    assert result.absolute_change == -2.0
    assert result.relative_change == pytest.approx(-0.2)
    assert mean([1.0, 2.0, 3.0]) == 2.0


def test_repeat_validates_count():
    assert len(repeat(lambda: 4, 2)) == 2
    with pytest.raises(ValueError):
        repeat(lambda: 4, 0)


def test_result_and_csv_writers(tmp_path):
    result_path = write_result(
        ExperimentResult(track="a", profile="quick", status=RunStatus.NOT_RUN, seed=1),
        tmp_path / "nested" / "summary.json",
    )
    assert json.loads(result_path.read_text())["status"] == "NOT RUN"
    csv_path = write_rows([{"method": "baseline", "score": 3}], tmp_path / "raw.csv")
    assert csv_path.read_text().splitlines() == ["method,score", "baseline,3"]


def test_svg_writer(tmp_path):
    path = write_bar_svg(["baseline", "method"], [2.0, 1.0], tmp_path / "plot.svg", "Observed")
    contents = path.read_text()
    assert contents.startswith("<svg")
    assert "baseline" in contents
