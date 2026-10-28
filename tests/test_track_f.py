import itertools

import pytest

from optlab.track_f import (
    FIXED_ORDER,
    PASS_FUNCTIONS,
    TRAINING_SOURCE,
    apply_passes,
    common_subexpression_elimination,
    compile_source,
    evaluate_ast,
    execute_code,
    execute_ir,
    generate_programs,
    lex,
    lower,
    optimize_pass_order_dp,
    parse,
)


def test_lexer_parser_precedence_and_three_execution_layers_agree():
    source = "a = 2 + 3 * 4; b = -(a - 20); print b + a;"
    assert any(token.kind == "PRINT" for token in lex(source))
    compilation = compile_source(source, FIXED_ORDER)
    expected = (20,)
    assert evaluate_ast(compilation.program) == expected
    assert execute_ir(compilation.original_ir) == expected
    assert execute_ir(compilation.optimized_ir) == expected
    assert execute_code(compilation.code) == expected


def test_each_of_four_passes_changes_targeted_ir_without_changing_output():
    sources = {
        "constant_folding": "x = 2 + 3; print x;",
        "constant_propagation": "a = 2; x = a + 3; print x;",
        "dead_code_elimination": "a = 2; dead = a * 4; print a;",
        "common_subexpression_elimination": "a=2; b=3; x=(a+b)*2; y=(a+b)*3; print x+y;",
    }
    assert set(sources) == set(PASS_FUNCTIONS)
    for name, source in sources.items():
        original = lower(parse(source))
        optimized = PASS_FUNCTIONS[name](original)
        assert optimized != original, name
        assert execute_ir(optimized) == execute_ir(original), name


def test_cse_does_not_cross_mutable_assignment_boundary():
    source = "a=2; b=3; old=a+b; a=10; new=a+b; print old; print new;"
    original = lower(parse(source))
    optimized = common_subexpression_elimination(original)
    assert execute_ir(original) == (5, 13)
    assert execute_ir(optimized) == (5, 13)


def test_dynamic_programming_finds_global_best_pass_order_on_training_program():
    original = lower(parse(TRAINING_SOURCE))
    plan = optimize_pass_order_dp(original)
    all_results = [apply_passes(original, order) for order in itertools.permutations(PASS_FUNCTIONS)]
    scores = [(len(ir), sum(len(item.text()) + 1 for item in ir)) for ir in all_results]
    assert (plan.instruction_count, plan.code_size_bytes) == min(scores)
    assert set(plan.order) == set(PASS_FUNCTIONS)
    assert execute_ir(plan.instructions) == execute_ir(original)


def test_generated_programs_are_equivalent_before_and_after_optimization():
    plan = optimize_pass_order_dp(lower(parse(TRAINING_SOURCE)))
    for source in generate_programs(30):
        compilation = compile_source(source, plan.order)
        expected = evaluate_ast(compilation.program)
        assert execute_ir(compilation.original_ir) == expected
        assert execute_ir(compilation.optimized_ir) == expected
        assert execute_code(compilation.code) == expected


def test_undefined_variables_and_bad_syntax_are_rejected():
    with pytest.raises(NameError, match="undefined variable"):
        lower(parse("x = missing + 1; print x;"))
    with pytest.raises(SyntaxError):
        parse("x = 1 print x;")
