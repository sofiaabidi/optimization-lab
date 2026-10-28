import itertools

import numpy as np
import pennylane as qml

from optlab.track_b import cut_value, load_maxcut_instance
from optlab.track_c import (
    apply_qaoa,
    barren_plateau_sample,
    exact_vqe_ground_energy,
    make_vqe_energy,
    maxcut_hamiltonian,
    optimize_vqe,
    parameter_shift_gradient,
    qaoa_noise_experiment,
)


def test_maxcut_hamiltonian_reuses_track_b_energy_for_every_basis_state():
    hamiltonian, mapping = maxcut_hamiltonian()
    matrix = qml.matrix(hamiltonian, wire_order=range(mapping["instance"]["nodes"]))
    assert np.allclose(matrix, np.diag(np.diag(matrix)))
    for bits in itertools.product((0, 1), repeat=mapping["instance"]["nodes"]):
        index = int("".join(map(str, bits)), 2)
        assert np.isclose(matrix[index, index].real, -cut_value(bits, load_maxcut_instance()))


def test_qaoa_is_an_actual_normalized_circuit():
    _, mapping = maxcut_hamiltonian()
    device = qml.device("default.qubit", wires=mapping["instance"]["nodes"])

    @qml.qnode(device)
    def probabilities(parameters):
        apply_qaoa(parameters, mapping)
        return qml.probs(wires=range(mapping["instance"]["nodes"]))

    result = probabilities(np.array([[0.2, 0.4], [0.3, 0.1]]))
    assert len(result) == 16
    assert np.isclose(np.sum(result), 1.0)


def test_parameter_shift_matches_finite_difference_and_vqe_bound():
    energy = make_vqe_energy()
    parameters = np.array([0.7, -0.4])
    shifted, evaluations = parameter_shift_gradient(energy, parameters)
    epsilon = 1e-6
    finite = np.array(
        [
            (energy(parameters + epsilon * np.eye(2)[index]) - energy(parameters - epsilon * np.eye(2)[index]))
            / (2 * epsilon)
            for index in range(2)
        ]
    )
    assert evaluations == 4
    assert np.allclose(shifted, finite, atol=1e-7)
    result = optimize_vqe("parameter_shift", evaluation_budget=60)
    assert result["energy"] >= exact_vqe_ground_energy() - 1e-10
    assert result["energy"] < result["history"][0]


def test_noise_and_barren_plateau_smokes_are_finite():
    noise = qaoa_noise_experiment(np.array([[0.2, 0.4], [0.3, 0.1]]), 0.01)
    assert np.isfinite(noise["energy"])
    assert 0.0 <= noise["optimal_probability"] <= 1.0
    assert np.isfinite(barren_plateau_sample(2, 1, 7))
