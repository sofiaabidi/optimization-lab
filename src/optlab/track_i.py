from __future__ import annotations

import csv
import json
import math
from fractions import Fraction
from pathlib import Path
from statistics import median
from time import perf_counter
from typing import Any, Callable, Sequence

import numpy as np
import pennylane as qml
from pennylane import numpy as pnp
from scipy.optimize import minimize

from .experiment import environment_metadata
from .models import ExperimentResult, RunStatus
from .plotting import write_bar_svg
from .track_b import cut_value, enumerate_maxcut, load_maxcut_instance

SEED = 2026


def _resource_fields(qnode: qml.QNode, *arguments: Any) -> dict[str, Any]:
    resources = qml.specs(qnode, compute_depth=True)(*arguments)["resources"]
    return {
        "gate_count": int(resources.num_gates),
        "circuit_depth": int(resources.depth),
        "gate_types": dict(resources.gate_types),
    }


def _timed_call(function: Callable[[], Any], repeats: int = 3) -> tuple[Any, float, list[float]]:
    function()  # untimed simulator/tape warmup
    durations = []
    result: Any = None
    for _ in range(repeats):
        started = perf_counter()
        result = function()
        durations.append(perf_counter() - started)
    return result, float(median(durations)), durations


def apply_parity_oracle(mask: Sequence[int], input_wires: Sequence[int], ancilla: int) -> None:
    """Manual reversible oracle f(x)=mask dot x mod 2."""
    for bit, wire in zip(mask, input_wires, strict=True):
        if bit:
            qml.CNOT(wires=[wire, ancilla])


def deutsch_jozsa_demo(mask: tuple[int, ...]) -> dict[str, Any]:
    if not mask or any(bit not in (0, 1) for bit in mask):
        raise ValueError("mask must be a non-empty binary tuple")
    inputs = tuple(range(len(mask)))
    ancilla = len(mask)
    device = qml.device("default.qubit", wires=len(mask) + 1)

    @qml.qnode(device)
    def circuit() -> Any:
        qml.PauliX(wires=ancilla)
        for wire in (*inputs, ancilla):
            qml.Hadamard(wires=wire)
        apply_parity_oracle(mask, inputs, ancilla)
        for wire in inputs:
            qml.Hadamard(wires=wire)
        return qml.probs(wires=inputs)

    probabilities, duration, raw = _timed_call(circuit)
    observed = int(np.argmax(probabilities))
    classification = "constant" if observed == 0 else "balanced"
    expected = "constant" if sum(mask) == 0 else "balanced"
    return {
        "algorithm": "Deutsch-Jozsa",
        "instance": "mask=" + "".join(map(str, mask)),
        "expected": expected,
        "observed": classification,
        "success_probability": float(probabilities[observed]),
        "qubits": len(mask) + 1,
        "oracle_queries": 1,
        "manual_gate_construction": True,
        "duration_seconds": duration,
        "timing_repeats_seconds": raw,
        **_resource_fields(circuit),
    }


def bernstein_vazirani_demo(secret: tuple[int, ...]) -> dict[str, Any]:
    if not secret or any(bit not in (0, 1) for bit in secret):
        raise ValueError("secret must be a non-empty binary tuple")
    inputs = tuple(range(len(secret)))
    ancilla = len(secret)
    device = qml.device("default.qubit", wires=len(secret) + 1)

    @qml.qnode(device)
    def circuit() -> Any:
        qml.PauliX(wires=ancilla)
        for wire in (*inputs, ancilla):
            qml.Hadamard(wires=wire)
        apply_parity_oracle(secret, inputs, ancilla)
        for wire in inputs:
            qml.Hadamard(wires=wire)
        return qml.probs(wires=inputs)

    probabilities, duration, raw = _timed_call(circuit)
    expected_index = int("".join(map(str, secret)), 2)
    observed = int(np.argmax(probabilities))
    return {
        "algorithm": "Bernstein-Vazirani",
        "instance": "secret=" + "".join(map(str, secret)),
        "expected": format(expected_index, f"0{len(secret)}b"),
        "observed": format(observed, f"0{len(secret)}b"),
        "success_probability": float(probabilities[expected_index]),
        "qubits": len(secret) + 1,
        "oracle_queries": 1,
        "manual_gate_construction": True,
        "duration_seconds": duration,
        "timing_repeats_seconds": raw,
        **_resource_fields(circuit),
    }


def apply_phase_oracle(target: int, wires: Sequence[int]) -> None:
    bits = tuple(int(bit) for bit in format(target, f"0{len(wires)}b"))
    for bit, wire in zip(bits, wires, strict=True):
        if bit == 0:
            qml.PauliX(wires=wire)
    qml.Hadamard(wires=wires[-1])
    qml.MultiControlledX(wires=list(wires))
    qml.Hadamard(wires=wires[-1])
    for bit, wire in zip(bits, wires, strict=True):
        if bit == 0:
            qml.PauliX(wires=wire)


def apply_grover_diffusion(wires: Sequence[int]) -> None:
    for wire in wires:
        qml.Hadamard(wires=wire)
        qml.PauliX(wires=wire)
    qml.Hadamard(wires=wires[-1])
    qml.MultiControlledX(wires=list(wires))
    qml.Hadamard(wires=wires[-1])
    for wire in wires:
        qml.PauliX(wires=wire)
        qml.Hadamard(wires=wire)


def apply_grover(target: int, wires: Sequence[int], iterations: int) -> None:
    for wire in wires:
        qml.Hadamard(wires=wire)
    for _ in range(iterations):
        apply_phase_oracle(target, wires)
        apply_grover_diffusion(wires)


def grover_demo(qubits: int = 3, target: int = 5) -> dict[str, Any]:
    if qubits < 2 or not 0 <= target < 2**qubits:
        raise ValueError("invalid Grover instance")
    wires = tuple(range(qubits))
    iterations = int(math.floor(math.pi * math.sqrt(2**qubits) / 4))
    device = qml.device("default.qubit", wires=qubits)

    @qml.qnode(device)
    def circuit() -> Any:
        apply_grover(target, wires, iterations)
        return qml.probs(wires=wires)

    probabilities, duration, raw = _timed_call(circuit)
    observed = int(np.argmax(probabilities))
    return {
        "algorithm": "Grover",
        "instance": f"N={2**qubits},target={target}",
        "expected": str(target),
        "observed": str(observed),
        "success_probability": float(probabilities[target]),
        "qubits": qubits,
        "oracle_queries": iterations,
        "manual_gate_construction": True,
        "duration_seconds": duration,
        "timing_repeats_seconds": raw,
        **_resource_fields(circuit),
    }


def apply_manual_qft(wires: Sequence[int]) -> None:
    """Textbook QFT from H, controlled phase, and SWAP gates only."""
    for position, target in enumerate(wires):
        qml.Hadamard(wires=target)
        for control_position in range(position + 1, len(wires)):
            angle = math.pi / (2 ** (control_position - position))
            qml.ControlledPhaseShift(angle, wires=[wires[control_position], target])
    for position in range(len(wires) // 2):
        qml.SWAP(wires=[wires[position], wires[-position - 1]])


def apply_inverse_manual_qft(wires: Sequence[int]) -> None:
    for position in reversed(range(len(wires) // 2)):
        qml.SWAP(wires=[wires[position], wires[-position - 1]])
    for position in reversed(range(len(wires))):
        for control_position in reversed(range(position + 1, len(wires))):
            angle = -math.pi / (2 ** (control_position - position))
            qml.ControlledPhaseShift(angle, wires=[wires[control_position], wires[position]])
        qml.Hadamard(wires=wires[position])


def qft_demo(qubits: int = 3, value: int = 5) -> dict[str, Any]:
    wires = tuple(range(qubits))
    bits = np.array([int(bit) for bit in format(value, f"0{qubits}b")])
    device = qml.device("default.qubit", wires=qubits)

    @qml.qnode(device)
    def transform() -> Any:
        qml.BasisState(bits, wires=wires)
        apply_manual_qft(wires)
        return qml.state()

    @qml.qnode(device)
    def round_trip() -> Any:
        qml.BasisState(bits, wires=wires)
        apply_manual_qft(wires)
        apply_inverse_manual_qft(wires)
        return qml.probs(wires=wires)

    state, duration, raw = _timed_call(transform)
    recovered = np.asarray(round_trip(), dtype=float)
    expected_magnitudes = np.full(2**qubits, 1 / math.sqrt(2**qubits))
    magnitude_error = float(np.max(np.abs(np.abs(state) - expected_magnitudes)))
    return {
        "algorithm": "Quantum Fourier Transform",
        "instance": f"{qubits}-qubit basis {value}",
        "expected": str(value),
        "observed": str(int(np.argmax(recovered))),
        "success_probability": float(recovered[value]),
        "uniform_magnitude_max_error": magnitude_error,
        "qubits": qubits,
        "oracle_queries": 0,
        "manual_gate_construction": True,
        "duration_seconds": duration,
        "timing_repeats_seconds": raw,
        **_resource_fields(transform),
    }


def qpe_demo(phase: float = 3 / 8, estimation_qubits: int = 3) -> dict[str, Any]:
    estimation = tuple(range(estimation_qubits))
    target_wire = estimation_qubits
    device = qml.device("default.qubit", wires=estimation_qubits + 1)

    @qml.qnode(device)
    def circuit() -> Any:
        qml.PauliX(wires=target_wire)  # eigenstate |1> of PhaseShift
        for wire in estimation:
            qml.Hadamard(wires=wire)
        for position, control in enumerate(estimation):
            power = 2 ** (estimation_qubits - position - 1)
            qml.ControlledPhaseShift(2 * math.pi * phase * power, wires=[control, target_wire])
        apply_inverse_manual_qft(estimation)
        return qml.probs(wires=estimation)

    probabilities, duration, raw = _timed_call(circuit)
    expected = int(round(phase * 2**estimation_qubits)) % (2**estimation_qubits)
    observed = int(np.argmax(probabilities))
    return {
        "algorithm": "Quantum Phase Estimation",
        "instance": f"phase={phase}",
        "expected": format(expected, f"0{estimation_qubits}b"),
        "observed": format(observed, f"0{estimation_qubits}b"),
        "success_probability": float(probabilities[expected]),
        "qubits": estimation_qubits + 1,
        "oracle_queries": sum(2 ** (estimation_qubits - position - 1) for position in range(estimation_qubits)),
        "manual_gate_construction": True,
        "duration_seconds": duration,
        "timing_repeats_seconds": raw,
        **_resource_fields(circuit),
    }


def modular_multiplication_matrix(base: int, modulus: int, work_qubits: int) -> np.ndarray:
    dimension = 2**work_qubits
    if math.gcd(base, modulus) != 1 or modulus > dimension:
        raise ValueError("base must be coprime to modulus and modulus must fit work register")
    matrix = np.zeros((dimension, dimension), dtype=complex)
    for value in range(dimension):
        transformed = (base * value) % modulus if value < modulus else value
        matrix[transformed, value] = 1.0
    if not np.allclose(matrix.conj().T @ matrix, np.eye(dimension)):
        raise ValueError("modular multiplication map is not unitary")
    return matrix


def shor_15_demo() -> dict[str, Any]:
    modulus, base = 15, 2
    estimation_qubits, work_qubits = 3, 4
    estimation = tuple(range(estimation_qubits))
    work = tuple(range(estimation_qubits, estimation_qubits + work_qubits))
    unitary = modular_multiplication_matrix(base, modulus, work_qubits)
    device = qml.device("default.qubit", wires=estimation_qubits + work_qubits)

    @qml.qnode(device)
    def circuit() -> Any:
        qml.PauliX(wires=work[-1])  # work register starts at |0001>
        for wire in estimation:
            qml.Hadamard(wires=wire)
        for position, control in enumerate(estimation):
            power = 2 ** (estimation_qubits - position - 1)
            powered = np.linalg.matrix_power(unitary, power)
            qml.ControlledQubitUnitary(powered, wires=[control, *work])
        apply_inverse_manual_qft(estimation)
        return qml.probs(wires=estimation)

    probabilities, duration, raw = _timed_call(circuit)
    peak_indices = [index for index, probability in enumerate(probabilities) if probability > 0.10]
    denominators = [
        Fraction(index, 2**estimation_qubits).limit_denominator(modulus).denominator
        for index in peak_indices
        if index != 0
    ]
    order = math.lcm(*denominators) if denominators else 0
    factors: list[int] = []
    if order > 0 and order % 2 == 0:
        factors = sorted(
            factor
            for factor in {math.gcd(base ** (order // 2) - 1, modulus), math.gcd(base ** (order // 2) + 1, modulus)}
            if factor not in {1, modulus}
        )
    useful_probability = sum(float(probabilities[index]) for index in peak_indices if index not in {0, 4})
    return {
        "algorithm": "Shor compiled order finding",
        "instance": "N=15,a=2",
        "expected": "3,5",
        "observed": ",".join(map(str, factors)),
        "success_probability": useful_probability,
        "recovered_order": order,
        "phase_peaks": peak_indices,
        "qubits": estimation_qubits + work_qubits,
        "oracle_queries": sum(2 ** (estimation_qubits - position - 1) for position in range(estimation_qubits)),
        "manual_gate_construction": False,
        "duration_seconds": duration,
        "timing_repeats_seconds": raw,
        "scope": "compiled N=15 demonstration using explicit controlled modular-multiplication unitaries",
        **_resource_fields(circuit),
    }


def grover_noise_experiment(target: int, probability: float, qubits: int = 3) -> dict[str, Any]:
    wires = tuple(range(qubits))
    iterations = int(math.floor(math.pi * math.sqrt(2**qubits) / 4))
    device = qml.device("default.mixed", wires=qubits)

    @qml.qnode(device)
    def circuit() -> Any:
        for wire in wires:
            qml.Hadamard(wires=wire)
        for _ in range(iterations):
            apply_phase_oracle(target, wires)
            apply_grover_diffusion(wires)
            if probability > 0:
                for wire in wires:
                    qml.DepolarizingChannel(probability, wires=wire)
        return qml.probs(wires=wires)

    started = perf_counter()
    probabilities = np.asarray(circuit(), dtype=float)
    return {
        "depolarizing_probability_per_wire_iteration": probability,
        "target_probability": float(probabilities[target]),
        "most_likely": int(np.argmax(probabilities)),
        "duration_seconds": perf_counter() - started,
        "simulator": "PennyLane default.mixed density matrix",
    }


def grover_shot_experiment(target: int, shots: int, seed: int, qubits: int = 3) -> dict[str, Any]:
    wires = tuple(range(qubits))
    iterations = int(math.floor(math.pi * math.sqrt(2**qubits) / 4))
    device = qml.device("default.qubit", wires=qubits, shots=shots, seed=seed)

    @qml.qnode(device)
    def circuit() -> Any:
        apply_grover(target, wires, iterations)
        return qml.sample(wires=wires)

    started = perf_counter()
    samples = np.asarray(circuit(), dtype=int)
    values = samples @ (2 ** np.arange(qubits - 1, -1, -1))
    fraction = float(np.mean(values == target))
    return {
        "shots": shots,
        "seed": seed,
        "target_fraction": fraction,
        "binomial_standard_error": math.sqrt(fraction * (1 - fraction) / shots),
        "duration_seconds": perf_counter() - started,
    }


def grover_classical_comparison(qubits: int = 3, target: int = 5, repeats: int = 20) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    quantum = grover_demo(qubits, target)
    wires = tuple(range(qubits))
    iterations = int(quantum["oracle_queries"])
    device = qml.device("default.qubit", wires=qubits)

    @qml.qnode(device)
    def quantum_circuit() -> Any:
        apply_grover(target, wires, iterations)
        return qml.probs(wires=wires)

    quantum_circuit()
    rows = []
    quantum_times = []
    classical_times = []
    classical_queries = target + 1
    for repeat in range(repeats):
        started = perf_counter()
        probabilities = quantum_circuit()
        quantum_elapsed = perf_counter() - started
        quantum_times.append(quantum_elapsed)
        started = perf_counter()
        found = next(value for value in range(2**qubits) if value == target)
        classical_elapsed = perf_counter() - started
        classical_times.append(classical_elapsed)
        rows.extend(
            (
                {"method": "Grover statevector simulation", "repeat": repeat, "wall_seconds": quantum_elapsed},
                {"method": "classical ascending linear search", "repeat": repeat, "wall_seconds": classical_elapsed},
            )
        )
        if int(np.argmax(probabilities)) != target or found != target:
            raise RuntimeError("search implementation returned the wrong target")
    comparison = {
        "database_size": 2**qubits,
        "target": target,
        "grover_oracle_queries": iterations,
        "grover_asymptotic_queries": "O(sqrt(N))",
        "grover_gate_count": quantum["gate_count"],
        "grover_circuit_depth": quantum["circuit_depth"],
        "grover_success_probability": quantum["success_probability"],
        "grover_simulator_median_seconds": float(median(quantum_times)),
        "classical_actual_queries": classical_queries,
        "classical_worst_case_queries": 2**qubits,
        "classical_asymptotic_queries": "O(N)",
        "classical_median_seconds": float(median(classical_times)),
        "limitation": "statevector wall time includes simulator/tape overhead and is not quantum hardware runtime",
    }
    return comparison, rows


def simulated_annealing_maxcut(runs: int = 20, sweeps: int = 120) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    instance = load_maxcut_instance()
    _, exact = enumerate_maxcut(instance)
    optimum = float(exact["optimum"]["cut_value"])
    rows = []
    started_all = perf_counter()
    for run in range(runs):
        rng = np.random.default_rng(SEED + run)
        bits = rng.integers(0, 2, size=instance["nodes"])
        value = cut_value(tuple(int(bit) for bit in bits), instance)
        best = value
        evaluations = 1
        started = perf_counter()
        for step in range(sweeps):
            temperature = 2.5 * (0.03 / 2.5) ** (step / max(1, sweeps - 1))
            wire = int(rng.integers(0, instance["nodes"]))
            proposal = bits.copy()
            proposal[wire] = 1 - proposal[wire]
            proposal_value = cut_value(tuple(int(bit) for bit in proposal), instance)
            evaluations += 1
            delta = proposal_value - value
            if delta >= 0 or rng.random() < math.exp(delta / temperature):
                bits, value = proposal, proposal_value
            best = max(best, value)
        rows.append(
            {
                "run": run,
                "best_cut": best,
                "exact_optimum": optimum,
                "success": math.isclose(best, optimum),
                "objective_evaluations": evaluations,
                "duration_seconds": perf_counter() - started,
            }
        )
    return {
        "method": "classical Metropolis simulated annealing",
        "runs": runs,
        "sweeps": sweeps,
        "success_rate": float(np.mean([row["success"] for row in rows])),
        "best_cut": max(row["best_cut"] for row in rows),
        "exact_optimum": optimum,
        "duration_seconds": perf_counter() - started_all,
        "quantum_hardware": False,
    }, rows


def make_qml_dataset(n_train: int = 24, n_test: int = 16, seed: int = SEED) -> tuple[np.ndarray, ...]:
    if n_train % 2 or n_test % 2:
        raise ValueError("balanced train/test sizes must be even")
    rng = np.random.default_rng(seed)
    by_label: dict[int, list[np.ndarray]] = {-1: [], 1: []}
    while min(len(values) for values in by_label.values()) < (n_train + n_test) // 2:
        point = rng.uniform(-math.pi, math.pi, size=2)
        label = 1 if math.cos(point[0]) * math.cos(point[1]) >= 0 else -1
        by_label[label].append(point)
    train_parts = []
    test_parts = []
    labels_train = []
    labels_test = []
    for label in (-1, 1):
        values = np.asarray(by_label[label])
        train_parts.append(values[: n_train // 2])
        test_parts.append(values[n_train // 2 : (n_train + n_test) // 2])
        labels_train.extend([label] * (n_train // 2))
        labels_test.extend([label] * (n_test // 2))
    x_train = np.vstack(train_parts)
    x_test = np.vstack(test_parts)
    y_train = np.asarray(labels_train, dtype=float)
    y_test = np.asarray(labels_test, dtype=float)
    train_order = rng.permutation(n_train)
    test_order = rng.permutation(n_test)
    return x_train[train_order], y_train[train_order], x_test[test_order], y_test[test_order]


def apply_feature_map(features: Sequence[float]) -> None:
    qml.RY(features[0], wires=0)
    qml.RY(features[1], wires=1)
    qml.CZ(wires=[0, 1])
    qml.RZ(features[0] * features[1] / math.pi, wires=1)


def quantum_kernel_matrices(x_train: np.ndarray, x_test: np.ndarray) -> tuple[np.ndarray, np.ndarray, int, float]:
    device = qml.device("default.qubit", wires=2)

    @qml.qnode(device)
    def overlap(first: np.ndarray, second: np.ndarray) -> Any:
        apply_feature_map(first)
        qml.adjoint(apply_feature_map)(second)
        return qml.probs(wires=[0, 1])

    started = perf_counter()
    train_count, test_count = len(x_train), len(x_test)
    train_kernel = np.eye(train_count)
    evaluations = 0
    for first in range(train_count):
        for second in range(first + 1, train_count):
            value = float(overlap(x_train[first], x_train[second])[0])
            train_kernel[first, second] = train_kernel[second, first] = value
            evaluations += 1
    test_kernel = np.empty((test_count, train_count))
    for first in range(test_count):
        for second in range(train_count):
            test_kernel[first, second] = float(overlap(x_test[first], x_train[second])[0])
            evaluations += 1
    return train_kernel, test_kernel, evaluations, perf_counter() - started


def _kernel_ridge(train_kernel: np.ndarray, test_kernel: np.ndarray, labels: np.ndarray, regularization: float = 0.1) -> np.ndarray:
    coefficients = np.linalg.solve(train_kernel + regularization * np.eye(len(train_kernel)), labels)
    scores = test_kernel @ coefficients
    return np.where(scores >= 0, 1.0, -1.0)


def quantum_kernel_comparison(
    x_train: np.ndarray, y_train: np.ndarray, x_test: np.ndarray, y_test: np.ndarray
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    quantum_train, quantum_test, evaluations, quantum_kernel_seconds = quantum_kernel_matrices(x_train, x_test)
    started = perf_counter()
    quantum_predictions = _kernel_ridge(quantum_train, quantum_test, y_train)
    quantum_solve_seconds = perf_counter() - started

    started = perf_counter()
    gamma = 0.5
    train_distances = np.sum((x_train[:, None, :] - x_train[None, :, :]) ** 2, axis=2)
    test_distances = np.sum((x_test[:, None, :] - x_train[None, :, :]) ** 2, axis=2)
    rbf_train = np.exp(-gamma * train_distances)
    rbf_test = np.exp(-gamma * test_distances)
    rbf_predictions = _kernel_ridge(rbf_train, rbf_test, y_train)
    rbf_seconds = perf_counter() - started
    rows = [
        {
            "model": "quantum fidelity kernel ridge",
            "test_accuracy": float(np.mean(quantum_predictions == y_test)),
            "train_seconds": quantum_kernel_seconds + quantum_solve_seconds,
            "parameter_count": 0,
            "circuit_evaluations": evaluations,
            "simulator": "default.qubit analytic",
        },
        {
            "model": "classical RBF kernel ridge",
            "test_accuracy": float(np.mean(rbf_predictions == y_test)),
            "train_seconds": rbf_seconds,
            "parameter_count": 1,
            "circuit_evaluations": 0,
            "simulator": "none",
        },
    ]
    prediction_rows = [
        {
            "test_index": index,
            "label": int(y_test[index]),
            "quantum_kernel_prediction": int(quantum_predictions[index]),
            "rbf_prediction": int(rbf_predictions[index]),
        }
        for index in range(len(y_test))
    ]
    return rows, {"predictions": prediction_rows, "quantum_train_kernel": quantum_train.tolist()}


def variational_classifier_comparison(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_test: np.ndarray,
    y_test: np.ndarray,
    steps: int = 35,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    device = qml.device("default.qubit", wires=2)

    @qml.qnode(device, interface="autograd", diff_method="parameter-shift")
    def circuit(features: Any, parameters: Any) -> Any:
        apply_feature_map(features)
        qml.RY(parameters[0], wires=0)
        qml.RY(parameters[1], wires=1)
        qml.CNOT(wires=[0, 1])
        qml.RZ(parameters[2], wires=0)
        qml.RY(parameters[3], wires=1)
        return qml.expval(qml.PauliZ(1))

    train_features = pnp.array(x_train, requires_grad=False)
    train_labels = pnp.array(y_train, requires_grad=False)
    parameters = pnp.array([0.05, -0.05, 0.02, -0.02, 0.0], requires_grad=True)

    def predictions(values: Any, features: Any) -> Any:
        return pnp.stack([circuit(point, values[:4]) + values[4] for point in features])

    def loss(values: Any) -> Any:
        return pnp.mean((predictions(values, train_features) - train_labels) ** 2)

    optimizer = qml.AdamOptimizer(stepsize=0.08)
    history = [{"step": 0, "loss": float(loss(parameters))}]
    started = perf_counter()
    with qml.Tracker(device) as tracker:
        for step in range(1, steps + 1):
            parameters = optimizer.step(loss, parameters)
            history.append({"step": step, "loss": float(loss(parameters))})
        test_scores = np.asarray(predictions(parameters, pnp.array(x_test, requires_grad=False)), dtype=float)
    quantum_seconds = perf_counter() - started
    quantum_predictions = np.where(test_scores >= 0, 1.0, -1.0)

    def classical_features(values: np.ndarray) -> np.ndarray:
        return np.column_stack(
            (
                np.ones(len(values)),
                np.sin(values[:, 0]),
                np.sin(values[:, 1]),
                np.cos(values[:, 0]),
                np.cos(values[:, 1]),
                np.cos(values[:, 0]) * np.cos(values[:, 1]),
            )
        )

    phi_train = classical_features(x_train)
    phi_test = classical_features(x_test)

    def logistic_objective(weights: np.ndarray) -> tuple[float, np.ndarray]:
        margins = y_train * (phi_train @ weights)
        losses = np.logaddexp(0.0, -margins)
        probabilities = 1.0 / (1.0 + np.exp(margins))
        gradient = -(phi_train.T @ (y_train * probabilities)) / len(y_train) + 0.01 * weights
        return float(np.mean(losses) + 0.005 * weights @ weights), gradient

    started = perf_counter()
    classical_result = minimize(
        lambda weights: logistic_objective(weights),
        np.zeros(phi_train.shape[1]),
        jac=True,
        method="BFGS",
        options={"maxiter": 100},
    )
    classical_seconds = perf_counter() - started
    classical_predictions = np.where(phi_test @ classical_result.x >= 0, 1.0, -1.0)
    rows = [
        {
            "model": "two-qubit variational classifier",
            "test_accuracy": float(np.mean(quantum_predictions == y_test)),
            "train_seconds": quantum_seconds,
            "parameter_count": 5,
            "circuit_evaluations": int(tracker.totals.get("executions", 0)),
            "training_steps": steps,
            "simulator": "default.qubit analytic parameter-shift",
        },
        {
            "model": "classical trigonometric logistic regression",
            "test_accuracy": float(np.mean(classical_predictions == y_test)),
            "train_seconds": classical_seconds,
            "parameter_count": int(len(classical_result.x)),
            "circuit_evaluations": 0,
            "training_steps": int(classical_result.nit),
            "simulator": "none",
        },
    ]
    prediction_rows = [
        {
            "test_index": index,
            "label": int(y_test[index]),
            "variational_prediction": int(quantum_predictions[index]),
            "classical_prediction": int(classical_predictions[index]),
        }
        for index in range(len(y_test))
    ]
    return rows, history, prediction_rows


def _write_csv(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = list(dict.fromkeys(key for row in rows for key in row))
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def run_experiment(profile: str = "quick", output_dir: Path | None = None) -> ExperimentResult:
    if profile not in {"quick", "full"}:
        raise ValueError("profile must be quick or full")
    if profile == "full":
        return ExperimentResult(
            track="i",
            profile="full",
            status=RunStatus.NOT_RUN,
            message="full quantum breadth/QML profile was not run",
        )
    total_started = perf_counter()
    output_dir = output_dir or Path("results/i")
    output_dir.mkdir(parents=True, exist_ok=True)

    algorithm_rows = [
        deutsch_jozsa_demo((0, 0, 0)),
        deutsch_jozsa_demo((1, 0, 1)),
        bernstein_vazirani_demo((1, 0, 1)),
        grover_demo(),
        qft_demo(),
        qpe_demo(),
        shor_15_demo(),
    ]
    algorithm_timing_rows = []
    for row in algorithm_rows:
        timings = row.pop("timing_repeats_seconds")
        gate_types = row.pop("gate_types")
        row["gate_types_json"] = json.dumps(gate_types, sort_keys=True)
        for repeat, elapsed in enumerate(timings):
            algorithm_timing_rows.append(
                {"algorithm": row["algorithm"], "instance": row["instance"], "repeat": repeat, "seconds": elapsed}
            )
    grover_comparison, search_timing_rows = grover_classical_comparison()
    shot_rows = [
        grover_shot_experiment(5, shots, SEED + 10 * shots + repeat)
        for shots in (128, 1024)
        for repeat in range(3)
    ]
    noise_rows = [grover_noise_experiment(5, probability) for probability in (0.0, 0.01, 0.03, 0.06)]
    annealing, annealing_rows = simulated_annealing_maxcut()

    x_train, y_train, x_test, y_test = make_qml_dataset()
    dataset_rows = [
        {"split": "train", "index": index, "x0": point[0], "x1": point[1], "label": int(label)}
        for index, (point, label) in enumerate(zip(x_train, y_train, strict=True))
    ] + [
        {"split": "test", "index": index, "x0": point[0], "x1": point[1], "label": int(label)}
        for index, (point, label) in enumerate(zip(x_test, y_test, strict=True))
    ]
    kernel_rows, kernel_details = quantum_kernel_comparison(x_train, y_train, x_test, y_test)
    variational_rows, variational_history, variational_predictions = variational_classifier_comparison(
        x_train, y_train, x_test, y_test
    )
    qml_rows = kernel_rows + variational_rows

    _write_csv(output_dir / "algorithms.csv", algorithm_rows)
    _write_csv(output_dir / "algorithm_timing_raw.csv", algorithm_timing_rows)
    _write_csv(output_dir / "grover_search_timing.csv", search_timing_rows)
    _write_csv(output_dir / "grover_shots.csv", shot_rows)
    _write_csv(output_dir / "grover_noise.csv", noise_rows)
    _write_csv(output_dir / "annealing_runs.csv", annealing_rows)
    _write_csv(output_dir / "qml_dataset.csv", dataset_rows)
    _write_csv(output_dir / "qml_comparison.csv", qml_rows)
    _write_csv(output_dir / "vqc_history.csv", variational_history)
    _write_csv(output_dir / "kernel_predictions.csv", kernel_details["predictions"])
    _write_csv(output_dir / "vqc_predictions.csv", variational_predictions)
    (output_dir / "quantum_kernel_train.json").write_text(
        json.dumps(kernel_details["quantum_train_kernel"], indent=2) + "\n", encoding="utf-8"
    )
    summary = {
        "profile": "quick",
        "date": "2026-10-29",
        "seed": SEED,
        "environment": {
            **environment_metadata(),
            "pennylane": qml.__version__,
            "simulators": ["default.qubit statevector", "default.mixed density matrix"],
            "hardware": "none",
        },
        "algorithm_correctness": {
            row["algorithm"] + ":" + row["instance"]: row["expected"] == row["observed"] for row in algorithm_rows
        },
        "manual_circuits": [row["algorithm"] for row in algorithm_rows if row["manual_gate_construction"]],
        "grover_vs_classical": grover_comparison,
        "annealing": annealing,
        "qml_comparison": qml_rows,
        "track_c_cross_reference": {
            "qaoa": "src/optlab/track_c.py::apply_qaoa and results/c/qaoa_optimization.csv",
            "vqe": "src/optlab/track_c.py::apply_vqe_ansatz and results/c/optimizer_comparison.csv",
            "barren_plateau": "results/c/barren_plateau_summary.csv",
        },
        "syllabus_status": "The authoritative Chapter 6 deck is still absent; all algorithms explicitly listed by plan.md are implemented, but additional taught algorithms remain unreconciled.",
        "full_profile_status": "NOT RUN",
        "limitations": [
            "All quantum results are local CPU simulations; no hardware or quantum advantage is claimed.",
            "The Shor circuit is a compiled N=15 order-finding demonstration, not scalable modular arithmetic.",
            "The annealer is a classical Metropolis simulator, not a quantum annealer.",
            "Grover statevector wall time includes simulator/tape overhead and is much slower than classical search here.",
            "The depolarizing model is synthetic and not calibrated to hardware.",
            "QML uses 24 training and 16 held-out synthetic points; accuracy is not a broad generalization result.",
            "Quantum kernel overlaps use analytic statevector circuits; finite-shot kernel estimation is not run.",
        ],
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_bar_svg(
        [row["model"].replace("quantum ", "q-").replace("classical ", "c-") for row in qml_rows],
        [row["test_accuracy"] for row in qml_rows],
        output_dir / "qml_accuracy.svg",
        "Track I held-out accuracy (same seeded splits)",
    )
    write_bar_svg(
        [f"p={row['depolarizing_probability_per_wire_iteration']:.2f}" for row in noise_rows],
        [row["target_probability"] for row in noise_rows],
        output_dir / "grover_noise.svg",
        "Grover target probability under synthetic depolarizing noise",
    )
    return ExperimentResult(
        track="i",
        profile="quick",
        status=RunStatus.DONE,
        method="named quantum circuits, classical annealing, and matched QML comparisons",
        objective=float(next(row["test_accuracy"] for row in qml_rows if row["model"].startswith("quantum fidelity"))),
        duration_seconds=perf_counter() - total_started,
        seed=SEED,
        message="executed named PennyLane simulator circuits and held-out QML/classical comparisons",
        metrics={
            "named_algorithm_checks_passed": all(summary["algorithm_correctness"].values()),
            "grover_target_probability": grover_comparison["grover_success_probability"],
            "quantum_kernel_accuracy": kernel_rows[0]["test_accuracy"],
            "classical_rbf_accuracy": kernel_rows[1]["test_accuracy"],
            "variational_accuracy": variational_rows[0]["test_accuracy"],
            "classical_logistic_accuracy": variational_rows[1]["test_accuracy"],
        },
        metadata={**environment_metadata(), "pennylane": qml.__version__},
    )
