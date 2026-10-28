import itertools

import numpy as np

from optlab.track_b import (
    branch_and_bound_knapsack,
    brute_force_knapsack,
    cardinality_penalty_demo,
    cut_value,
    dynamic_programming_knapsack,
    enumerate_maxcut,
    greedy_knapsack,
    ising_energy,
    load_maxcut_instance,
    make_knapsack,
    maxcut_qubo,
    milp_knapsack,
    qubo_energy,
    qubo_to_ising,
)


def test_knapsack_exact_methods_match_brute_force_oracle():
    instance = make_knapsack()
    oracle = brute_force_knapsack(instance)
    for solver in (dynamic_programming_knapsack, branch_and_bound_knapsack, milp_knapsack):
        result = solver(instance)
        assert result.feasible(instance.capacity)
        assert result.value == oracle.value
    greedy = greedy_knapsack(instance)
    assert greedy.feasible(instance.capacity)
    assert greedy.value < oracle.value


def test_maxcut_qubo_and_ising_match_every_bitstring():
    instance = load_maxcut_instance()
    matrix = maxcut_qubo(instance)
    constant, fields, couplings = qubo_to_ising(matrix)
    for bits in itertools.product((0, 1), repeat=instance["nodes"]):
        cut = cut_value(bits, instance)
        qubo = qubo_energy(bits, matrix)
        ising = ising_energy(bits, constant, fields, couplings)
        assert qubo == -cut
        assert np.isclose(ising, qubo, atol=1e-12)


def test_enumerated_maxcut_optimum_and_mapping_errors():
    rows, mapping = enumerate_maxcut(load_maxcut_instance())
    assert len(rows) == 16
    assert mapping["optimum"]["cut_value"] == max(row["cut_value"] for row in rows)
    assert mapping["max_abs_qubo_plus_cut_error"] < 1e-12
    assert mapping["max_abs_qubo_minus_ising_error"] < 1e-12


def test_cardinality_penalty_transitions_to_feasible_solution():
    rows = cardinality_penalty_demo()
    assert rows[0]["feasible_exactly_one"] is False
    assert rows[-1]["feasible_exactly_one"] is True
    assert rows[-1]["selected_count"] == 1
