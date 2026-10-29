import csv

import numpy as np

from optlab.track_i import (
    bernstein_vazirani_demo,
    deutsch_jozsa_demo,
    grover_classical_comparison,
    grover_demo,
    grover_noise_experiment,
    make_qml_dataset,
    modular_multiplication_matrix,
    qft_demo,
    qpe_demo,
    quantum_kernel_matrices,
    shor_15_demo,
    simulated_annealing_maxcut,
    variational_classifier_comparison,
    _write_csv,
)


def test_deutsch_jozsa_and_bernstein_vazirani_match_analytic_oracles():
    constant = deutsch_jozsa_demo((0, 0, 0))
    balanced = deutsch_jozsa_demo((1, 0, 1))
    bernstein = bernstein_vazirani_demo((1, 0, 1))
    assert constant["observed"] == constant["expected"] == "constant"
    assert balanced["observed"] == balanced["expected"] == "balanced"
    assert bernstein["observed"] == bernstein["expected"] == "101"
    assert min(constant["success_probability"], balanced["success_probability"], bernstein["success_probability"]) > 0.999
    assert all(result["manual_gate_construction"] for result in (constant, balanced, bernstein))


def test_manual_grover_qft_and_qpe_have_known_outputs():
    grover = grover_demo()
    qft = qft_demo()
    qpe = qpe_demo()
    assert grover["observed"] == grover["expected"] == "5"
    assert grover["oracle_queries"] == 2
    assert grover["success_probability"] > 0.94
    assert qft["observed"] == qft["expected"] == "5"
    assert qft["success_probability"] > 0.999
    assert qft["uniform_magnitude_max_error"] < 1e-12
    assert qpe["observed"] == qpe["expected"] == "011"
    assert qpe["success_probability"] > 0.999


def test_compiled_shor_order_finding_is_unitary_and_factors_15():
    matrix = modular_multiplication_matrix(2, 15, 4)
    assert np.allclose(matrix.conj().T @ matrix, np.eye(16))
    result = shor_15_demo()
    assert result["recovered_order"] == 4
    assert result["observed"] == result["expected"] == "3,5"
    assert result["phase_peaks"] == [0, 2, 4, 6]
    assert np.isclose(result["success_probability"], 0.5)
    assert "compiled" in result["scope"]


def test_grover_query_accounting_and_noise_are_truthful():
    comparison, rows = grover_classical_comparison(repeats=3)
    assert comparison["grover_oracle_queries"] == 2
    assert comparison["classical_actual_queries"] == 6
    assert comparison["classical_worst_case_queries"] == 8
    assert len(rows) == 6
    noiseless = grover_noise_experiment(5, 0.0)
    noisy = grover_noise_experiment(5, 0.06)
    assert noisy["target_probability"] < noiseless["target_probability"]


def test_qml_uses_reproducible_identical_splits_and_valid_kernels():
    first = make_qml_dataset(n_train=8, n_test=4)
    second = make_qml_dataset(n_train=8, n_test=4)
    assert all(np.array_equal(left, right) for left, right in zip(first, second, strict=True))
    x_train, y_train, x_test, y_test = first
    assert set(y_train) == set(y_test) == {-1.0, 1.0}
    train_kernel, test_kernel, evaluations, _ = quantum_kernel_matrices(x_train, x_test)
    assert np.allclose(train_kernel, train_kernel.T)
    assert np.allclose(np.diag(train_kernel), 1.0)
    assert np.linalg.eigvalsh(train_kernel).min() > -1e-9
    assert test_kernel.shape == (4, 8)
    assert evaluations == 8 * 7 // 2 + 4 * 8
    models, history, predictions = variational_classifier_comparison(
        x_train, y_train, x_test, y_test, steps=2
    )
    assert len(models) == 2 and len(predictions) == len(y_test)
    assert models[0]["circuit_evaluations"] > 0
    assert history[-1]["loss"] <= history[0]["loss"]


def test_classical_annealing_is_labeled_and_checked_against_exact_optimum():
    summary, rows = simulated_annealing_maxcut(runs=5, sweeps=40)
    assert not summary["quantum_hardware"]
    assert summary["method"].startswith("classical")
    assert summary["best_cut"] <= summary["exact_optimum"]
    assert all(row["objective_evaluations"] == 41 for row in rows)


def test_heterogeneous_algorithm_artifacts_keep_union_of_fields(tmp_path):
    path = tmp_path / "algorithms.csv"
    _write_csv(path, [{"algorithm": "first", "common": 1}, {"algorithm": "second", "extra": 2}])
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0] == {"algorithm": "first", "common": "1", "extra": ""}
    assert rows[1] == {"algorithm": "second", "common": "", "extra": "2"}
