import numpy as np

from optlab.track_a import (
    backpropagation_check,
    finite_difference_gradient,
    gauss_newton_demo,
    landscape_examples,
    make_ridge_problem,
    run_first_order,
    run_newton,
)


def test_ridge_gradient_and_analytic_optimum():
    problem = make_ridge_problem(samples=32)
    point = np.array([0.3, -0.4, 0.2])
    assert np.max(np.abs(problem.gradient(point) - finite_difference_gradient(problem, point))) < 1e-8
    assert np.linalg.norm(problem.gradient(problem.optimum)) < 1e-10
    assert np.linalg.eigvalsh(problem.hessian).min() > 0


def test_first_order_methods_have_distinct_convergent_trajectories():
    problem = make_ridge_problem(samples=48)
    methods = {
        "gd": 0.2,
        "momentum": 0.08,
        "nag": 0.08,
        "adagrad": 0.2,
        "rmsprop": 0.03,
        "adam": 0.05,
        "sgd": 0.03,
        "mini_batch_sgd": 0.08,
    }
    runs = [run_first_order(problem, method, learning_rate=rate, steps=120, seed=5) for method, rate in methods.items()]
    assert all(run.history[-1] < run.history[0] for run in runs)
    assert len({tuple(np.round(run.history[:5], 10)) for run in runs}) == len(runs)
    assert all(np.isfinite(run.history[-1]) for run in runs)


def test_newton_gauss_newton_and_backprop_oracles():
    problem = make_ridge_problem(samples=40)
    newton = run_newton(problem)
    assert np.linalg.norm(newton.weights - problem.optimum) < 1e-10
    gauss_newton = gauss_newton_demo()
    assert gauss_newton["parameter_error_l2"] < 1e-7
    check = backpropagation_check(problem)
    assert check["manual_vs_autograd_max_abs"] < 1e-10
    assert check["manual_vs_finite_difference_max_abs"] < 1e-8


def test_landscape_examples_identify_local_global_and_saddle():
    examples = landscape_examples()
    scopes = {point.get("scope") for point in examples["nonconvex_stationary_points"]}
    assert {"local", "global"} <= scopes
    assert examples["saddle"]["hessian_eigenvalues"] == [-2.0, 2.0]
    assert examples["continuous_vs_discrete"]["integer_optimum_by_enumeration"] == 2
    convex = examples["convex_not_strongly_convex"]
    assert convex["gd_final_objective"] < convex["gd_start_objective"]
