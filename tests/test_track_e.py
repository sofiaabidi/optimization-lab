import numpy as np

from optlab.track_e import (
    brute_force_grid_objective,
    cheapest_slot_schedule,
    exact_lp_schedule,
    first_available_schedule,
    make_feasible_instance,
    make_fleet_instance,
    make_infeasible_instance,
    schedule_cost,
    tiny_oracle_instance,
    verify_schedule,
)


def test_all_methods_are_independently_feasible_and_optimized_costs_improve():
    instance = make_feasible_instance()
    baseline = first_available_schedule(instance)
    heuristic = cheapest_slot_schedule(instance)
    exact = exact_lp_schedule(instance)
    for result in (baseline, heuristic, exact):
        assert result.schedule_kwh is not None
        assert verify_schedule(instance, result.schedule_kwh).feasible
    assert schedule_cost(instance, exact.schedule_kwh) <= schedule_cost(instance, heuristic.schedule_kwh) + 1e-8
    assert schedule_cost(instance, heuristic.schedule_kwh) < schedule_cost(instance, baseline.schedule_kwh)


def test_infeasible_case_is_not_presented_as_feasible():
    instance = make_infeasible_instance()
    exact = exact_lp_schedule(instance)
    assert exact.status == "INFEASIBLE"
    assert exact.schedule_kwh is None
    for result in (first_available_schedule(instance), cheapest_slot_schedule(instance)):
        assert result.status == "PARTIAL_INFEASIBLE"
        assert result.schedule_kwh is not None
        check = verify_schedule(instance, result.schedule_kwh)
        assert not check.feasible
        assert check.unmet_energy_kwh > 0


def test_verifier_rejects_capacity_rate_window_and_energy_errors():
    instance = make_feasible_instance()
    result = exact_lp_schedule(instance)
    assert result.schedule_kwh is not None
    broken = result.schedule_kwh.copy()
    broken[0, -1] = 1.0
    check = verify_schedule(instance, broken)
    assert not check.feasible
    assert check.max_window_violation_kwh == 1.0
    assert check.max_energy_error_kwh >= 1.0

    overloaded = np.zeros_like(broken)
    overloaded[:, 2] = 2.0
    check = verify_schedule(instance, overloaded)
    assert not check.feasible
    assert check.max_capacity_violation_kwh > 0


def test_lp_objective_matches_independent_tiny_grid_oracle():
    instance = tiny_oracle_instance()
    result = exact_lp_schedule(instance)
    assert result.schedule_kwh is not None
    assert verify_schedule(instance, result.schedule_kwh).feasible
    assert np.isclose(schedule_cost(instance, result.schedule_kwh), brute_force_grid_objective(instance), atol=1e-9)


def test_seeded_fleet_generation_is_reproducible():
    first = make_fleet_instance(8)
    second = make_fleet_instance(8)
    assert first.vehicles == second.vehicles
    assert np.array_equal(first.prices_per_kwh, second.prices_per_kwh)
    assert np.array_equal(first.facility_kw, second.facility_kw)
