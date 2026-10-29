from pathlib import Path

from optlab.models import RunStatus
from optlab.track_j import (
    MUTATIONS,
    PRE_J_EXCLUSIONS,
    alphabetical_selection,
    build_coverage,
    count_maintained_source_loc,
    exact_maximum_coverage_ilp,
    features_for_node,
    greedy_maximum_coverage,
    repository_root,
    run_experiment,
    selection_objective,
)


def test_repository_cleared_source_loc_gate_before_track_j_additions():
    root = repository_root()
    total, rows = count_maintained_source_loc(root / "src" / "optlab", PRE_J_EXCLUSIONS)
    assert total >= 1_000
    assert rows
    assert all(not row["file"].endswith(("track_j.py", "pytest_profile.py")) for row in rows)
    assert all("tests/" not in row["file"] for row in rows)


def test_feature_mapping_is_grounded_in_component_and_test_behavior():
    nodeid = "tests/test_track_b.py::test_maxcut_qubo_and_ising_match_every_bitstring"
    features = set(features_for_node(nodeid))
    assert "component:track_b" in features
    assert "behavior:track_b:maxcut_qubo_and_ising_match_every_bitstring" in features
    assert "shared:maxcut_representation" in features
    assert "cross:semantic_equivalence" in features


def test_alphabetical_greedy_and_exact_selection_respect_budget_and_objective():
    nodes = ["a", "b", "c"]
    costs = {"a": 2.0, "b": 2.0, "c": 3.0}
    coverage = {"a": {"x"}, "b": {"y"}, "c": {"x", "y", "z"}}
    weights = {"x": 1.0, "y": 1.0, "z": 1.0}
    budget = 4.0
    alphabetical = alphabetical_selection(nodes, costs, budget)
    greedy = greedy_maximum_coverage(nodes, costs, coverage, weights, budget)
    exact = exact_maximum_coverage_ilp(nodes, costs, coverage, weights, budget)
    for selected in (alphabetical, greedy, exact):
        assert sum(costs[node] for node in selected) <= budget
    assert selection_objective(greedy, coverage, weights) >= selection_objective(alphabetical, coverage, weights)
    assert selection_objective(exact, coverage, weights) >= selection_objective(greedy, coverage, weights)


def test_fault_matrix_credits_only_observed_scoped_failures():
    nodes = [
        "tests/test_track_a.py::test_one",
        "tests/test_track_a.py::test_two",
        "tests/test_track_b.py::test_three",
    ]
    mutations = [
        {
            "fault_id": "M1",
            "failing_tests": [nodes[1]],
            "test_scope": "tests/test_track_a.py",
        }
    ]
    coverage, weights, _, matrix = build_coverage(nodes, mutations)
    assert "fault:M1" in coverage[nodes[1]]
    assert "fault:M1" not in coverage[nodes[0]]
    assert weights["fault:M1"] > 1.0
    assert sum(row["detected_in_scoped_run"] for row in matrix) == 1


def test_mutation_targets_are_unique_and_full_profile_is_truthful():
    root = repository_root()
    for mutation in MUTATIONS:
        contents = (root / mutation.source_file).read_text(encoding="utf-8")
        assert contents.count(mutation.original) == 1
        assert mutation.original != mutation.replacement
        assert (root / mutation.test_file).exists()
    result = run_experiment("full", output_dir=Path("unused"))
    assert result.status == RunStatus.NOT_RUN
