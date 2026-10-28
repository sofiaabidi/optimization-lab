from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

import numpy as np
import pennylane as qml
from pennylane import numpy as pnp
from scipy.optimize import minimize

from .experiment import environment_metadata
from .models import ExperimentResult, RunStatus
from .plotting import write_bar_svg
from .track_b import enumerate_maxcut, ising_energy, load_maxcut_instance, maxcut_qubo, qubo_to_ising

SEED = 2026


def maxcut_hamiltonian() -> tuple[qml.Hamiltonian, dict[str, Any]]:
    instance = load_maxcut_instance()
    matrix = maxcut_qubo(instance)
    constant, fields, couplings = qubo_to_ising(matrix)
    coefficients: list[float] = [constant]
    observables: list[qml.operation.Operator] = [qml.Identity(0)]
    for wire, field in enumerate(fields):
        if abs(field) > 1e-15:
            coefficients.append(float(field))
            observables.append(qml.PauliZ(wire))
    for i in range(instance["nodes"]):
        for j in range(i + 1, instance["nodes"]):
            if abs(couplings[i, j]) > 1e-15:
                coefficients.append(float(couplings[i, j]))
                observables.append(qml.PauliZ(i) @ qml.PauliZ(j))
    mapping = {
        "instance": instance,
        "constant": constant,
        "fields": fields,
        "couplings": couplings,
        "qubo_matrix": matrix,
    }
    return qml.Hamiltonian(coefficients, observables), mapping


def apply_qaoa(parameters: Any, mapping: dict[str, Any]) -> None:
    nodes = mapping["instance"]["nodes"]
    for wire in range(nodes):
        qml.Hadamard(wires=wire)
    layers = int(parameters.shape[1])
    for layer in range(layers):
        gamma = parameters[0, layer]
        beta = parameters[1, layer]
        for wire, field in enumerate(mapping["fields"]):
            if abs(field) > 1e-15:
                qml.RZ(2 * gamma * field, wires=wire)
        for i in range(nodes):
            for j in range(i + 1, nodes):
                coupling = mapping["couplings"][i, j]
                if abs(coupling) > 1e-15:
                    qml.IsingZZ(2 * gamma * coupling, wires=[i, j])
        for wire in range(nodes):
            qml.RX(2 * beta, wires=wire)


def optimize_qaoa(layers: int = 2, max_evaluations: int = 100) -> dict[str, Any]:
    hamiltonian, mapping = maxcut_hamiltonian()
    nodes = mapping["instance"]["nodes"]
    device = qml.device("default.qubit", wires=nodes)

    @qml.qnode(device)
    def energy(parameters: np.ndarray) -> Any:
        apply_qaoa(parameters, mapping)
        return qml.expval(hamiltonian)

    evaluations = 0
    history: list[dict[str, float]] = []

    def objective(flat_parameters: np.ndarray) -> float:
        nonlocal evaluations
        evaluations += 1
        value = float(energy(flat_parameters.reshape(2, layers)))
        history.append({"evaluation": evaluations, "energy": value})
        return value

    initial = np.array([[0.35, 0.75], [0.55, 0.25]], dtype=float)[:, :layers]
    started = perf_counter()
    result = minimize(
        objective,
        initial.ravel(),
        method="COBYLA",
        options={"maxiter": max_evaluations, "rhobeg": 0.35, "tol": 1e-7},
    )
    duration = perf_counter() - started
    parameters = result.x.reshape(2, layers)

    probability_device = qml.device("default.qubit", wires=nodes)

    @qml.qnode(probability_device)
    def probabilities(params: np.ndarray) -> Any:
        apply_qaoa(params, mapping)
        return qml.probs(wires=range(nodes))

    probs = np.asarray(probabilities(parameters), dtype=float)
    maxcut_rows, classical_mapping = enumerate_maxcut(mapping["instance"])
    optimum_cut = float(classical_mapping["optimum"]["cut_value"])
    optimal_bitstrings = sorted(row["bits"] for row in maxcut_rows if row["cut_value"] == optimum_cut)
    optimum_probability = sum(probs[int(bits, 2)] for bits in optimal_bitstrings)
    return {
        "layers": layers,
        "parameters": parameters.tolist(),
        "energy": float(energy(parameters)),
        "expectation_cut": -float(energy(parameters)),
        "classical_optimum_cut": optimum_cut,
        "optimal_bitstrings": optimal_bitstrings,
        "optimal_sample_probability": float(optimum_probability),
        "evaluations": evaluations + 2,
        "duration_seconds": duration,
        "optimizer": "COBYLA",
        "optimizer_success": bool(result.success),
        "optimizer_message": str(result.message),
        "history": history,
    }


def qaoa_shot_experiment(parameters: np.ndarray, shots: int, seed: int) -> dict[str, Any]:
    _, mapping = maxcut_hamiltonian()
    nodes = mapping["instance"]["nodes"]
    device = qml.device("default.qubit", wires=nodes, shots=shots, seed=seed)

    @qml.qnode(device)
    def sample_circuit(params: np.ndarray) -> Any:
        apply_qaoa(params, mapping)
        return qml.sample(wires=range(nodes))

    started = perf_counter()
    samples = np.asarray(sample_circuit(parameters), dtype=int)
    duration = perf_counter() - started
    energies = np.array(
        [ising_energy(tuple(sample), mapping["constant"], mapping["fields"], mapping["couplings"]) for sample in samples]
    )
    _, classical_mapping = enumerate_maxcut(mapping["instance"])
    optimum_energy = -float(classical_mapping["optimum"]["cut_value"])
    return {
        "shots": shots,
        "seed": seed,
        "estimated_energy": float(energies.mean()),
        "energy_standard_error": float(energies.std(ddof=1) / math.sqrt(shots)),
        "best_energy": float(energies.min()),
        "optimal_sample_fraction": float(np.mean(np.isclose(energies, optimum_energy))),
        "duration_seconds": duration,
    }


def qaoa_noise_experiment(parameters: np.ndarray, noise_probability: float) -> dict[str, Any]:
    hamiltonian, mapping = maxcut_hamiltonian()
    nodes = mapping["instance"]["nodes"]
    device = qml.device("default.mixed", wires=nodes)

    @qml.qnode(device)
    def noisy_circuit(params: np.ndarray) -> Any:
        for wire in range(nodes):
            qml.Hadamard(wires=wire)
        for layer in range(params.shape[1]):
            gamma = params[0, layer]
            beta = params[1, layer]
            for i in range(nodes):
                for j in range(i + 1, nodes):
                    coupling = mapping["couplings"][i, j]
                    if abs(coupling) > 1e-15:
                        qml.IsingZZ(2 * gamma * coupling, wires=[i, j])
            for wire in range(nodes):
                qml.RX(2 * beta, wires=wire)
                if noise_probability > 0:
                    qml.DepolarizingChannel(noise_probability, wires=wire)
        return qml.expval(hamiltonian), qml.probs(wires=range(nodes))

    started = perf_counter()
    energy, probabilities = noisy_circuit(parameters)
    duration = perf_counter() - started
    _, classical_mapping = enumerate_maxcut(mapping["instance"])
    optimum_cut = float(classical_mapping["optimum"]["cut_value"])
    optimal = [row["bits"] for row in enumerate_maxcut(mapping["instance"])[0] if row["cut_value"] == optimum_cut]
    optimum_probability = sum(float(probabilities[int(bits, 2)]) for bits in optimal)
    return {
        "depolarizing_probability_per_wire_layer": noise_probability,
        "energy": float(energy),
        "expectation_cut": -float(energy),
        "optimal_probability": optimum_probability,
        "duration_seconds": duration,
        "simulator": "default.mixed analytic density matrix",
    }


def vqe_hamiltonian() -> qml.Hamiltonian:
    return qml.Hamiltonian(
        [-1.0, -0.7, 0.3],
        [qml.PauliZ(0), qml.PauliZ(1), qml.PauliX(0) @ qml.PauliX(1)],
    )


def apply_vqe_ansatz(parameters: Any) -> None:
    qml.RY(parameters[0], wires=0)
    qml.RY(parameters[1], wires=1)
    qml.CNOT(wires=[0, 1])


def exact_vqe_ground_energy() -> float:
    matrix = qml.matrix(vqe_hamiltonian(), wire_order=[0, 1])
    return float(np.linalg.eigvalsh(matrix).min())


def make_vqe_energy() -> Callable[[np.ndarray], float]:
    device = qml.device("default.qubit", wires=2)
    hamiltonian = vqe_hamiltonian()

    @qml.qnode(device)
    def energy(parameters: Any) -> Any:
        apply_vqe_ansatz(parameters)
        return qml.expval(hamiltonian)

    return energy


def parameter_shift_gradient(energy: Callable[[np.ndarray], float], parameters: np.ndarray) -> tuple[np.ndarray, int]:
    gradient = np.zeros_like(parameters, dtype=float)
    for index in range(len(parameters)):
        plus = parameters.copy()
        minus = parameters.copy()
        plus[index] += np.pi / 2
        minus[index] -= np.pi / 2
        gradient[index] = 0.5 * (float(energy(plus)) - float(energy(minus)))
    return gradient, 2 * len(parameters)


def optimize_vqe(method: str, evaluation_budget: int = 300, seed: int = SEED) -> dict[str, Any]:
    if method not in {"parameter_shift", "spsa", "qng"}:
        raise ValueError(f"unknown VQE optimizer: {method}")
    energy = make_vqe_energy()
    parameters = np.array([0.7, -0.4], dtype=float)
    evaluations = 1
    history = [float(energy(parameters))]
    rng = np.random.default_rng(seed)
    started = perf_counter()
    iteration = 0
    while evaluations < evaluation_budget:
        iteration += 1
        if method == "spsa":
            if evaluations + 3 > evaluation_budget:
                break
            delta = rng.choice((-1.0, 1.0), size=len(parameters))
            c_k = 0.12 / iteration**0.101
            a_k = 0.18 / iteration**0.602
            plus = float(energy(parameters + c_k * delta))
            minus = float(energy(parameters - c_k * delta))
            gradient = (plus - minus) * delta / (2 * c_k)
            evaluations += 2
            parameters -= a_k * gradient
        else:
            required = 2 * len(parameters) + 1
            if evaluations + required > evaluation_budget:
                break
            gradient, used = parameter_shift_gradient(energy, parameters)
            evaluations += used
            if method == "parameter_shift":
                parameters -= 0.10 * gradient
            else:
                # Diagonal Fubini-Study metric for the two independent RY parameters.
                metric_diagonal = np.full(len(parameters), 0.25) + 1e-3
                parameters -= 0.025 * gradient / metric_diagonal
        history.append(float(energy(parameters)))
        evaluations += 1
    final_energy = history[-1]
    exact = exact_vqe_ground_energy()
    return {
        "method": method,
        "parameters": parameters.tolist(),
        "energy": final_energy,
        "exact_ground_energy": exact,
        "energy_error": final_energy - exact,
        "iterations": iteration,
        "circuit_evaluations": evaluations,
        "duration_seconds": perf_counter() - started,
        "history": history,
        "metric": "diagonal Fubini-Study 0.25 I plus 1e-3 damping" if method == "qng" else None,
    }


def train_qnn(steps: int = 80) -> dict[str, Any]:
    device = qml.device("default.qubit", wires=1)

    @qml.qnode(device, interface="autograd", diff_method="parameter-shift")
    def circuit(x: float, quantum_parameters: Any) -> Any:
        qml.RY(x, wires=0)
        qml.RZ(quantum_parameters[0], wires=0)
        qml.RY(quantum_parameters[1], wires=0)
        return qml.expval(qml.PauliZ(0))

    features = pnp.array([0.0, 0.4, 1.0, 2.1, 2.7, 3.1], requires_grad=False)
    labels = pnp.array([1.0, 1.0, 1.0, -1.0, -1.0, -1.0], requires_grad=False)
    parameters = pnp.array([0.2, -0.1, 1.0, 0.0], requires_grad=True)

    def predictions(values: Any) -> Any:
        quantum = values[:2]
        scale, bias = values[2], values[3]
        return pnp.stack([scale * circuit(x, quantum) + bias for x in features])

    def loss(values: Any) -> Any:
        return pnp.mean((predictions(values) - labels) ** 2)

    optimizer = qml.AdamOptimizer(stepsize=0.08)
    history = [float(loss(parameters))]
    started = perf_counter()
    with qml.Tracker(device) as tracker:
        for _ in range(steps):
            parameters = optimizer.step(loss, parameters)
            history.append(float(loss(parameters)))
    final_predictions = np.asarray(predictions(parameters), dtype=float)
    accuracy = float(np.mean(np.sign(final_predictions) == np.asarray(labels)))
    return {
        "loss_initial": history[0],
        "loss_final": history[-1],
        "accuracy": accuracy,
        "parameters": np.asarray(parameters, dtype=float).tolist(),
        "steps": steps,
        "circuit_executions": int(tracker.totals.get("executions", 0)),
        "duration_seconds": perf_counter() - started,
        "history": history,
        "description": "one-qubit PQC plus trainable classical scale and bias",
    }


def barren_plateau_sample(qubits: int, depth: int, seed: int) -> float:
    rng = np.random.default_rng(seed)
    parameters = pnp.array(rng.uniform(-np.pi, np.pi, size=(depth, qubits, 2)), requires_grad=True)
    device = qml.device("default.qubit", wires=qubits)
    observable: qml.operation.Operator = qml.PauliZ(0)
    for wire in range(1, qubits):
        observable = observable @ qml.PauliZ(wire)

    @qml.qnode(device, interface="autograd", diff_method="backprop")
    def circuit(values: Any) -> Any:
        for layer in range(depth):
            for wire in range(qubits):
                qml.RY(values[layer, wire, 0], wires=wire)
                qml.RZ(values[layer, wire, 1], wires=wire)
            for wire in range(qubits - 1):
                qml.CZ(wires=[wire, wire + 1])
            if qubits > 2:
                qml.CZ(wires=[qubits - 1, 0])
        return qml.expval(observable)

    gradient = qml.grad(circuit)(parameters)
    # The last-wire RY avoids an exact two-qubit parity cancellation at depth one.
    return float(gradient[0, qubits - 1, 0])


def barren_plateau_experiment(trials: int = 8) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    raw = []
    summary = []
    for qubits in (2, 4, 6):
        for depth in (1, 3, 5):
            values = []
            started = perf_counter()
            for trial in range(trials):
                gradient = barren_plateau_sample(qubits, depth, SEED + 100 * qubits + 10 * depth + trial)
                values.append(gradient)
                raw.append({"qubits": qubits, "depth": depth, "trial": trial, "gradient": gradient})
            summary.append(
                {
                    "qubits": qubits,
                    "depth": depth,
                    "trials": trials,
                    "gradient_mean": float(np.mean(values)),
                    "gradient_variance": float(np.var(values, ddof=1)),
                    "mean_absolute_gradient": float(np.mean(np.abs(values))),
                    "duration_seconds": perf_counter() - started,
                }
            )
    return raw, summary


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def run_experiment(profile: str = "quick", output_dir: Path | None = None) -> ExperimentResult:
    if profile not in {"quick", "full"}:
        raise ValueError("profile must be quick or full")
    total_started = perf_counter()
    output_dir = output_dir or Path("results/c")
    output_dir.mkdir(parents=True, exist_ok=True)
    qaoa = optimize_qaoa(layers=2, max_evaluations=180 if profile == "quick" else 350)
    parameters = np.asarray(qaoa["parameters"], dtype=float)
    repeats = 3 if profile == "quick" else 10
    shot_rows = [
        qaoa_shot_experiment(parameters, shots, SEED + repeat)
        for shots in ((100, 500, 2000) if profile == "quick" else (100, 1000, 10000))
        for repeat in range(repeats)
    ]
    noise_rows = [qaoa_noise_experiment(parameters, probability) for probability in (0.0, 0.01, 0.03)]
    vqe_rows = [optimize_vqe(method, evaluation_budget=300, seed=SEED) for method in ("parameter_shift", "spsa", "qng")]
    qnn = train_qnn(steps=80 if profile == "quick" else 200)
    plateau_raw, plateau_summary = barren_plateau_experiment(trials=8 if profile == "quick" else 20)

    qaoa_history = qaoa.pop("history")
    optimizer_history_rows = []
    for result in vqe_rows:
        history = result.pop("history")
        for step, energy in enumerate(history):
            optimizer_history_rows.append({"method": result["method"], "step": step, "energy": energy})
    qnn_history = qnn.pop("history")
    summary = {
        "profile": profile,
        "seed": SEED,
        "environment": {**environment_metadata(), "pennylane": qml.__version__, "simulator": "PennyLane default.qubit/default.mixed"},
        "qaoa": qaoa,
        "vqe_optimizer_comparison": vqe_rows,
        "qnn": qnn,
        "barren_plateau_summary": plateau_summary,
        "annealer_embedding_limitation": (
            "The logical Max-Cut graph contains triangle 0-1-2. A four-site path hardware graph has no triangle, "
            "so direct one-logical-to-one-physical placement is impossible; at least one logical variable needs a "
            "multi-qubit chain and a chain-strength penalty. This consumes extra qubits and can distort the QUBO energy scale."
        ),
        "full_profile_status": "DONE" if profile == "full" else "NOT RUN",
        "limitations": [
            "All results are local CPU simulations; no quantum hardware was used.",
            "The four-node QAOA result and two-qubit VQE cannot establish quantum advantage.",
            "The depolarizing channel is a plausible synthetic noise model, not calibration from a device.",
            "The barren-plateau sweep is a finite-size illustration; non-monotone sample variance is possible.",
            "QNG uses a documented diagonal Fubini-Study approximation rather than the full metric tensor.",
        ],
    }
    _write_csv(output_dir / "qaoa_optimization.csv", qaoa_history)
    _write_csv(output_dir / "qaoa_shots.csv", shot_rows)
    _write_csv(output_dir / "qaoa_noise.csv", noise_rows)
    _write_csv(output_dir / "optimizer_comparison.csv", vqe_rows)
    _write_csv(output_dir / "optimizer_histories.csv", optimizer_history_rows)
    _write_csv(output_dir / "qnn_history.csv", [{"step": step, "loss": loss} for step, loss in enumerate(qnn_history)])
    _write_csv(output_dir / "barren_plateau_raw.csv", plateau_raw)
    _write_csv(output_dir / "barren_plateau_summary.csv", plateau_summary)
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_bar_svg(
        [f"n={row['qubits']},d={row['depth']}" for row in plateau_summary],
        [row["gradient_variance"] for row in plateau_summary],
        output_dir / "barren_plateau_variance.svg",
        "Measured random-circuit gradient variance",
    )
    write_bar_svg(
        [row["method"].replace("_", " ") for row in vqe_rows],
        [max(row["energy_error"], 0.0) for row in vqe_rows],
        output_dir / "vqe_energy_error.svg",
        "VQE energy error at comparable evaluation budget",
    )
    return ExperimentResult(
        track="c",
        profile=profile,
        status=RunStatus.DONE,
        method="qaoa-vqe-qnn-simulator-study",
        objective=float(qaoa["energy"]),
        duration_seconds=perf_counter() - total_started,
        seed=SEED,
        message=f"wrote measured Track C simulator artifacts to {output_dir}",
        metrics={
            "qaoa_expectation_cut": qaoa["expectation_cut"],
            "classical_maxcut_optimum": qaoa["classical_optimum_cut"],
            "qaoa_optimal_probability": qaoa["optimal_sample_probability"],
            "vqe_exact_ground_energy": exact_vqe_ground_energy(),
            "qnn_accuracy": qnn["accuracy"],
        },
        metadata={**environment_metadata(), "pennylane": qml.__version__},
    )
