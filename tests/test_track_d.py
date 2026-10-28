import numpy as np

from optlab.track_d import (
    centralized_training,
    data_parallel_demo,
    exhaustive_coverage,
    fedavg_training,
    greedy_coverage,
    make_federated_data,
    mgda_coefficient,
    model_parallel_demo,
    multitask_training,
    pipeline_parallel_demo,
    verify_diminishing_returns,
)


def test_coverage_is_submodular_and_greedy_is_checked_by_oracle():
    verification = verify_diminishing_returns()
    greedy_selection, greedy_value = greedy_coverage(3)
    exact_selection, exact_value = exhaustive_coverage(3)
    assert verification["passed"] is True
    assert verification["checks"] > 0
    assert len(greedy_selection) == len(exact_selection) == 3
    assert greedy_value <= exact_value


def test_real_parallel_patterns_preserve_results_and_use_distinct_processes():
    for result in (
        data_parallel_demo(workers=2, samples=200, features=4),
        model_parallel_demo(workers=2, samples=200, features=4),
        pipeline_parallel_demo(items=6, rounds=1_000),
    ):
        assert result["actually_parallel"] is True
        assert len(result["worker_pids"]) == 2
        assert result["max_abs_error"] < 1e-10


def test_fedavg_and_centralized_share_data_and_improve_initial_loss():
    data = make_federated_data()
    initial_loss = centralized_training(data, steps=1)["history"][0]["loss"]
    centralized = centralized_training(data, steps=20)
    federated = fedavg_training(data, local_steps=2, rounds=10)
    assert centralized["train_loss"] < initial_loss
    assert federated["train_loss"] < initial_loss
    assert federated["communication_bytes"] > 0
    assert 0.0 <= centralized["test_accuracy"] <= 1.0
    assert 0.0 <= federated["test_accuracy"] <= 1.0


def test_mgda_and_multitask_weights_are_valid():
    coefficient = mgda_coefficient(np.array([1.0, 0.0]), np.array([0.0, 1.0]))
    assert 0.0 <= coefficient <= 1.0
    for method in ("equal", "mgda", "gradnorm"):
        result = multitask_training(method, steps=30)
        assert np.isfinite(result["task_one_loss"])
        assert np.isfinite(result["task_two_loss"])
        assert result["task_one_weight"] > 0
        assert result["task_two_weight"] > 0
        assert np.isclose(result["task_one_weight"] + result["task_two_weight"], 1.0)
