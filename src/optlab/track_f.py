from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Iterable, Sequence

import numpy as np

from .experiment import environment_metadata
from .models import ExperimentResult, RunStatus
from .plotting import write_bar_svg

SEED = 2026


@dataclass(frozen=True)
class Token:
    kind: str
    text: str
    position: int


TOKEN_PATTERN = re.compile(
    r"(?P<SPACE>\s+)|(?P<NUMBER>\d+)|(?P<IDENT>[A-Za-z_][A-Za-z0-9_]*)|(?P<SYMBOL>[+*()=;\-])|(?P<BAD>.)"
)


def lex(source: str) -> tuple[Token, ...]:
    tokens: list[Token] = []
    for match in TOKEN_PATTERN.finditer(source):
        kind = match.lastgroup or "BAD"
        text = match.group()
        if kind == "SPACE":
            continue
        if kind == "BAD":
            raise SyntaxError(f"unexpected character {text!r} at position {match.start()}")
        if kind == "IDENT" and text == "print":
            kind = "PRINT"
        tokens.append(Token(kind, text, match.start()))
    tokens.append(Token("EOF", "", len(source)))
    return tuple(tokens)


@dataclass(frozen=True)
class Number:
    value: int


@dataclass(frozen=True)
class Variable:
    name: str


@dataclass(frozen=True)
class Binary:
    operator: str
    left: Expression
    right: Expression


Expression = Number | Variable | Binary


@dataclass(frozen=True)
class Assignment:
    name: str
    expression: Expression


@dataclass(frozen=True)
class Print:
    expression: Expression


Statement = Assignment | Print


@dataclass(frozen=True)
class Program:
    statements: tuple[Statement, ...]


class Parser:
    def __init__(self, tokens: Sequence[Token]):
        self.tokens = tokens
        self.position = 0

    @property
    def current(self) -> Token:
        return self.tokens[self.position]

    def accept(self, kind: str, text: str | None = None) -> Token | None:
        token = self.current
        if token.kind == kind and (text is None or token.text == text):
            self.position += 1
            return token
        return None

    def expect(self, kind: str, text: str | None = None) -> Token:
        token = self.accept(kind, text)
        if token is None:
            expected = text if text is not None else kind
            raise SyntaxError(f"expected {expected!r} at position {self.current.position}")
        return token

    def parse(self) -> Program:
        statements: list[Statement] = []
        while self.current.kind != "EOF":
            statements.append(self.statement())
        if not statements:
            raise SyntaxError("program must contain at least one statement")
        return Program(tuple(statements))

    def statement(self) -> Statement:
        if self.accept("PRINT") is not None:
            expression = self.expression()
            self.expect("SYMBOL", ";")
            return Print(expression)
        name = self.expect("IDENT").text
        self.expect("SYMBOL", "=")
        expression = self.expression()
        self.expect("SYMBOL", ";")
        return Assignment(name, expression)

    def expression(self) -> Expression:
        expression = self.term()
        while self.current.kind == "SYMBOL" and self.current.text in {"+", "-"}:
            operator = self.current.text
            self.position += 1
            expression = Binary(operator, expression, self.term())
        return expression

    def term(self) -> Expression:
        expression = self.factor()
        while self.current.kind == "SYMBOL" and self.current.text == "*":
            self.position += 1
            expression = Binary("*", expression, self.factor())
        return expression

    def factor(self) -> Expression:
        if (number := self.accept("NUMBER")) is not None:
            return Number(int(number.text))
        if (identifier := self.accept("IDENT")) is not None:
            return Variable(identifier.text)
        if self.accept("SYMBOL", "-") is not None:
            return Binary("-", Number(0), self.factor())
        if self.accept("SYMBOL", "(") is not None:
            expression = self.expression()
            self.expect("SYMBOL", ")")
            return expression
        raise SyntaxError(f"expected expression at position {self.current.position}")


def parse(source: str) -> Program:
    return Parser(lex(source)).parse()


def _evaluate_expression(expression: Expression, environment: dict[str, int]) -> int:
    if isinstance(expression, Number):
        return expression.value
    if isinstance(expression, Variable):
        if expression.name not in environment:
            raise NameError(f"undefined variable {expression.name!r}")
        return environment[expression.name]
    left = _evaluate_expression(expression.left, environment)
    right = _evaluate_expression(expression.right, environment)
    return _arithmetic(expression.operator, left, right)


def evaluate_ast(program: Program) -> tuple[int, ...]:
    environment: dict[str, int] = {}
    output: list[int] = []
    for statement in program.statements:
        if isinstance(statement, Assignment):
            environment[statement.name] = _evaluate_expression(statement.expression, environment)
        else:
            output.append(_evaluate_expression(statement.expression, environment))
    return tuple(output)


Operand = int | str


@dataclass(frozen=True)
class IRInstruction:
    operation: str
    destination: str | None = None
    left: Operand | None = None
    right: Operand | None = None

    def text(self) -> str:
        fields = [self.operation]
        for field in (self.destination, self.left, self.right):
            if field is not None:
                fields.append(str(field))
        return " ".join(fields)


IR = tuple[IRInstruction, ...]


class Lowerer:
    def __init__(self) -> None:
        self.instructions: list[IRInstruction] = []
        self.defined: set[str] = set()
        self.next_temporary = 0

    def temporary(self) -> str:
        name = f"%{self.next_temporary}"
        self.next_temporary += 1
        return name

    def expression(self, expression: Expression, destination: str | None = None) -> Operand:
        if isinstance(expression, Number):
            if destination is None:
                return expression.value
            self.instructions.append(IRInstruction("CONST", destination, expression.value))
            return destination
        if isinstance(expression, Variable):
            if expression.name not in self.defined:
                raise NameError(f"undefined variable {expression.name!r}")
            if destination is None:
                return expression.name
            self.instructions.append(IRInstruction("MOV", destination, expression.name))
            return destination
        left = self.expression(expression.left)
        right = self.expression(expression.right)
        target = destination or self.temporary()
        operation = {"+": "ADD", "-": "SUB", "*": "MUL"}[expression.operator]
        self.instructions.append(IRInstruction(operation, target, left, right))
        return target

    def lower(self, program: Program) -> IR:
        for statement in program.statements:
            if isinstance(statement, Assignment):
                self.expression(statement.expression, statement.name)
                self.defined.add(statement.name)
            else:
                value = self.expression(statement.expression)
                self.instructions.append(IRInstruction("PRINT", left=value))
        return tuple(self.instructions)


def lower(program: Program) -> IR:
    return Lowerer().lower(program)


def _arithmetic(operation: str, left: int, right: int) -> int:
    if operation in {"+", "ADD"}:
        return left + right
    if operation in {"-", "SUB"}:
        return left - right
    if operation in {"*", "MUL"}:
        return left * right
    raise ValueError(f"unsupported arithmetic operation {operation!r}")


def _read(operand: Operand | None, environment: dict[str, int]) -> int:
    if isinstance(operand, int):
        return operand
    if isinstance(operand, str) and operand in environment:
        return environment[operand]
    raise NameError(f"undefined IR operand {operand!r}")


def execute_ir(instructions: IR) -> tuple[int, ...]:
    environment: dict[str, int] = {}
    output: list[int] = []
    for instruction in instructions:
        if instruction.operation == "PRINT":
            output.append(_read(instruction.left, environment))
        elif instruction.operation == "CONST":
            assert instruction.destination is not None
            environment[instruction.destination] = _read(instruction.left, environment)
        elif instruction.operation == "MOV":
            assert instruction.destination is not None
            environment[instruction.destination] = _read(instruction.left, environment)
        else:
            assert instruction.destination is not None
            environment[instruction.destination] = _arithmetic(
                instruction.operation,
                _read(instruction.left, environment),
                _read(instruction.right, environment),
            )
    return tuple(output)


def constant_folding(instructions: IR) -> IR:
    folded: list[IRInstruction] = []
    for instruction in instructions:
        if instruction.operation in {"ADD", "SUB", "MUL"} and isinstance(instruction.left, int) and isinstance(instruction.right, int):
            folded.append(
                IRInstruction(
                    "CONST",
                    instruction.destination,
                    _arithmetic(instruction.operation, instruction.left, instruction.right),
                )
            )
        else:
            folded.append(instruction)
    return tuple(folded)


def constant_propagation(instructions: IR) -> IR:
    constants: dict[str, int] = {}
    propagated: list[IRInstruction] = []
    for instruction in instructions:
        left = constants.get(instruction.left, instruction.left) if isinstance(instruction.left, str) else instruction.left
        right = constants.get(instruction.right, instruction.right) if isinstance(instruction.right, str) else instruction.right
        current = IRInstruction(instruction.operation, instruction.destination, left, right)
        if instruction.destination is not None:
            constants.pop(instruction.destination, None)
            if current.operation in {"CONST", "MOV"} and isinstance(current.left, int):
                constants[instruction.destination] = current.left
        propagated.append(current)
    return tuple(propagated)


def dead_code_elimination(instructions: IR) -> IR:
    live: set[str] = set()
    retained: list[IRInstruction] = []
    for instruction in reversed(instructions):
        if instruction.operation == "PRINT":
            retained.append(instruction)
            if isinstance(instruction.left, str):
                live.add(instruction.left)
            continue
        destination = instruction.destination
        if destination is None or destination not in live:
            continue
        retained.append(instruction)
        live.discard(destination)
        for operand in (instruction.left, instruction.right):
            if isinstance(operand, str):
                live.add(operand)
    return tuple(reversed(retained))


def common_subexpression_elimination(instructions: IR) -> IR:
    available: dict[tuple[str, Operand, Operand], str] = {}
    aliases: dict[str, str] = {}
    optimized: list[IRInstruction] = []

    def resolve(operand: Operand | None) -> Operand | None:
        while isinstance(operand, str) and operand in aliases:
            operand = aliases[operand]
        return operand

    for instruction in instructions:
        left = resolve(instruction.left)
        right = resolve(instruction.right)
        destination = instruction.destination
        if destination is not None:
            aliases.pop(destination, None)
            aliases = {name: value for name, value in aliases.items() if value != destination}
            available = {
                key: value
                for key, value in available.items()
                if destination not in key[1:] and value != destination
            }
        if instruction.operation in {"ADD", "SUB", "MUL"}:
            assert destination is not None and left is not None and right is not None
            if instruction.operation in {"ADD", "MUL"} and repr(left) > repr(right):
                left, right = right, left
            key = (instruction.operation, left, right)
            if key in available:
                producer = available[key]
                if destination.startswith("%"):
                    aliases[destination] = producer
                else:
                    optimized.append(IRInstruction("MOV", destination, producer))
                continue
            available[key] = destination
        optimized.append(IRInstruction(instruction.operation, destination, left, right))
    return tuple(optimized)


PASS_FUNCTIONS: dict[str, Callable[[IR], IR]] = {
    "constant_folding": constant_folding,
    "constant_propagation": constant_propagation,
    "dead_code_elimination": dead_code_elimination,
    "common_subexpression_elimination": common_subexpression_elimination,
}
FIXED_ORDER = tuple(PASS_FUNCTIONS)


def apply_passes(instructions: IR, order: Sequence[str]) -> IR:
    result = instructions
    for name in order:
        if name not in PASS_FUNCTIONS:
            raise ValueError(f"unknown optimization pass {name!r}")
        result = PASS_FUNCTIONS[name](result)
    return result


@dataclass(frozen=True)
class BytecodeInstruction:
    operation: str
    destination: str | None = None
    left: Operand | None = None
    right: Operand | None = None

    def text(self) -> str:
        return IRInstruction(self.operation, self.destination, self.left, self.right).text()


Bytecode = tuple[BytecodeInstruction, ...]


def generate_code(instructions: IR) -> Bytecode:
    return tuple(
        BytecodeInstruction(item.operation, item.destination, item.left, item.right)
        for item in instructions
    )


def encode_code(code: Bytecode) -> bytes:
    return ("\n".join(instruction.text() for instruction in code) + "\n").encode("utf-8")


def execute_code(code: Bytecode) -> tuple[int, ...]:
    environment: dict[str, int] = {}
    output: list[int] = []
    for instruction in code:
        if instruction.operation == "PRINT":
            output.append(_read(instruction.left, environment))
        elif instruction.operation in {"CONST", "MOV"}:
            assert instruction.destination is not None
            environment[instruction.destination] = _read(instruction.left, environment)
        else:
            assert instruction.destination is not None
            environment[instruction.destination] = _arithmetic(
                instruction.operation,
                _read(instruction.left, environment),
                _read(instruction.right, environment),
            )
    return tuple(output)


def ir_text(instructions: IR) -> str:
    return "\n".join(instruction.text() for instruction in instructions)


def _score(instructions: IR) -> tuple[int, int]:
    return len(instructions), len(encode_code(generate_code(instructions)))


@dataclass(frozen=True)
class PassPlan:
    order: tuple[str, ...]
    instructions: IR
    instruction_count: int
    code_size_bytes: int
    states_explored: int
    transitions: int
    final_candidates: tuple[tuple[tuple[str, ...], int, int], ...]


def optimize_pass_order_dp(instructions: IR) -> PassPlan:
    """Exact subset DP: apply every safe pass once, minimizing count then code bytes."""
    names = tuple(PASS_FUNCTIONS)
    full_mask = (1 << len(names)) - 1
    frontiers: dict[int, dict[IR, tuple[str, ...]]] = {0: {instructions: ()}}
    transitions = 0
    for mask in range(full_mask + 1):
        for current, order in tuple(frontiers.get(mask, {}).items()):
            for index, name in enumerate(names):
                bit = 1 << index
                if mask & bit:
                    continue
                transitions += 1
                candidate = PASS_FUNCTIONS[name](current)
                candidate_order = order + (name,)
                bucket = frontiers.setdefault(mask | bit, {})
                incumbent = bucket.get(candidate)
                if incumbent is None or candidate_order < incumbent:
                    bucket[candidate] = candidate_order
    final = [
        (order, candidate, _score(candidate))
        for candidate, order in frontiers[full_mask].items()
    ]
    order, optimized, score = min(final, key=lambda item: (item[2], item[0]))
    candidates = tuple(sorted((candidate_order, *candidate_score) for candidate_order, _, candidate_score in final))
    return PassPlan(
        order=order,
        instructions=optimized,
        instruction_count=score[0],
        code_size_bytes=score[1],
        states_explored=sum(len(states) for states in frontiers.values()),
        transitions=transitions,
        final_candidates=candidates,
    )


@dataclass(frozen=True)
class Compilation:
    program: Program
    original_ir: IR
    optimized_ir: IR
    code: Bytecode
    pass_order: tuple[str, ...]


def compile_source(source: str, pass_order: Sequence[str] = ()) -> Compilation:
    program = parse(source)
    original = lower(program)
    optimized = apply_passes(original, pass_order)
    return Compilation(program, original, optimized, generate_code(optimized), tuple(pass_order))


TRAINING_SOURCE = """
a = 100000;
b = a + 300000;
c = a + 300000;
unused = c * 10;
print (b + c) * (b + c);
"""


PROGRAMS: dict[str, str] = {
    "constant_chain": """
        a = 2 + 3;
        b = a * 4;
        dead = 99 * 2;
        c = b + (2 + 3);
        print c;
    """,
    "repeated_expression": """
        a = 7;
        b = 9;
        x = (a + b) * 2;
        y = (a + b) * 3;
        print x + y;
    """,
    "dead_overwrite": """
        value = 3 * 4;
        unused = value + 100;
        value = value + 2;
        print value;
    """,
    "adverse_reassignment": """
        a = 2;
        b = 3;
        old = a + b;
        a = 10;
        new = a + b;
        print old;
        print new;
    """,
    "minimal_program": """
        answer = 42;
        print answer;
    """,
}


def generate_programs(count: int = 20, seed: int = SEED) -> tuple[str, ...]:
    rng = np.random.default_rng(seed)
    programs: list[str] = []
    operators = ("+", "-", "*")
    for program_index in range(count):
        lines = [f"v0 = {int(rng.integers(0, 8))};"]
        for variable_index in range(1, 7):
            left = f"v{int(rng.integers(0, variable_index))}"
            if rng.random() < 0.5:
                right = str(int(rng.integers(0, 8)))
            else:
                right = f"v{int(rng.integers(0, variable_index))}"
            operator = operators[int(rng.integers(0, len(operators)))]
            lines.append(f"v{variable_index} = {left} {operator} {right};")
        lines.append(f"print v6 + {program_index % 3};")
        programs.append("\n".join(lines))
    return tuple(programs)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("cannot write an empty CSV")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _median_compile(source: str, order: tuple[str, ...], repeats: int) -> tuple[Compilation, float, list[float]]:
    durations = []
    compilations = []
    for _ in range(repeats):
        started = perf_counter()
        compilations.append(compile_source(source, order))
        durations.append(perf_counter() - started)
    median = float(np.median(durations))
    representative = compilations[min(range(repeats), key=lambda index: abs(durations[index] - median))]
    return representative, median, durations


def _median_execution(code: Bytecode, repeats: int, iterations: int) -> tuple[float, list[float]]:
    execute_code(code)
    durations = []
    for _ in range(repeats):
        started = perf_counter()
        for _ in range(iterations):
            execute_code(code)
        durations.append((perf_counter() - started) / iterations)
    return float(np.median(durations)), durations


def run_experiment(profile: str = "quick", output_dir: Path | None = None) -> ExperimentResult:
    if profile not in {"quick", "full"}:
        raise ValueError("profile must be quick or full")
    started = perf_counter()
    output_dir = output_dir or Path("results/f")
    output_dir.mkdir(parents=True, exist_ok=True)
    compile_repeats = 7 if profile == "quick" else 30
    execution_repeats = 7 if profile == "quick" else 20
    execution_iterations = 300 if profile == "quick" else 3000

    training_ir = lower(parse(TRAINING_SOURCE))
    plan_started = perf_counter()
    plan = optimize_pass_order_dp(training_ir)
    planning_seconds = perf_counter() - plan_started
    strategies = {
        "unoptimized": (),
        "fixed_order": FIXED_ORDER,
        "dp_order": plan.order,
    }

    benchmark_rows: list[dict[str, Any]] = []
    raw_rows: list[dict[str, Any]] = []
    equivalence_rows: list[dict[str, Any]] = []
    snapshots: dict[str, Any] = {}
    for program_name, source in PROGRAMS.items():
        expected = evaluate_ast(parse(source))
        snapshots[program_name] = {"source": source.strip(), "expected_output": list(expected), "strategies": {}}
        for strategy, order in strategies.items():
            compilation, compile_median, compile_durations = _median_compile(source, order, compile_repeats)
            execution_median, execution_durations = _median_execution(
                compilation.code, execution_repeats, execution_iterations
            )
            original_output = execute_ir(compilation.original_ir)
            optimized_output = execute_ir(compilation.optimized_ir)
            code_output = execute_code(compilation.code)
            equivalent = expected == original_output == optimized_output == code_output
            if not equivalent:
                raise RuntimeError(f"semantic mismatch for {program_name}/{strategy}")
            benchmark_rows.append(
                {
                    "program": program_name,
                    "strategy": strategy,
                    "pass_order": "|".join(order) if order else "none",
                    "instruction_count": len(compilation.code),
                    "code_size_bytes": len(encode_code(compilation.code)),
                    "compile_median_seconds": compile_median,
                    "execution_median_seconds": execution_median,
                    "output": json.dumps(code_output),
                    "equivalent": equivalent,
                }
            )
            for repeat, duration in enumerate(compile_durations):
                raw_rows.append(
                    {
                        "program": program_name,
                        "strategy": strategy,
                        "measurement": "compile",
                        "repeat": repeat,
                        "seconds": duration,
                        "iterations": 1,
                    }
                )
            for repeat, duration in enumerate(execution_durations):
                raw_rows.append(
                    {
                        "program": program_name,
                        "strategy": strategy,
                        "measurement": "execute_per_program",
                        "repeat": repeat,
                        "seconds": duration,
                        "iterations": execution_iterations,
                    }
                )
            equivalence_rows.append(
                {
                    "program": program_name,
                    "strategy": strategy,
                    "ast_output": json.dumps(expected),
                    "original_ir_output": json.dumps(original_output),
                    "optimized_ir_output": json.dumps(optimized_output),
                    "bytecode_output": json.dumps(code_output),
                    "equivalent": equivalent,
                }
            )
            snapshots[program_name]["strategies"][strategy] = {
                "pass_order": list(order),
                "original_ir": ir_text(compilation.original_ir),
                "optimized_ir": ir_text(compilation.optimized_ir),
                "bytecode": encode_code(compilation.code).decode("utf-8").rstrip(),
            }

    targeted_sources = {
        "constant_folding": "x = 2 + 3; print x;",
        "constant_propagation": "a = 2; x = a + 3; print x;",
        "dead_code_elimination": "a = 2; dead = a * 4; print a;",
        "common_subexpression_elimination": "a = 2; b = 3; x = (a + b) * 2; y = (a + b) * 3; print x + y;",
    }
    pass_rows = []
    for name, source in targeted_sources.items():
        original = lower(parse(source))
        transformed = PASS_FUNCTIONS[name](original)
        changed = transformed != original
        equivalent = execute_ir(original) == execute_ir(transformed)
        if not changed or not equivalent:
            raise RuntimeError(f"targeted pass gate failed for {name}")
        pass_rows.append(
            {
                "pass": name,
                "before_instructions": len(original),
                "after_instructions": len(transformed),
                "before_code_bytes": len(encode_code(generate_code(original))),
                "after_code_bytes": len(encode_code(generate_code(transformed))),
                "changed": changed,
                "equivalent": equivalent,
            }
        )

    generated_checked = 0
    for source in generate_programs(40 if profile == "quick" else 400):
        compilation = compile_source(source, plan.order)
        expected = evaluate_ast(compilation.program)
        if expected != execute_ir(compilation.original_ir) or expected != execute_ir(compilation.optimized_ir) or expected != execute_code(compilation.code):
            raise RuntimeError("generated-program semantic equivalence gate failed")
        generated_checked += 1

    search_rows = [
        {
            "order": "|".join(order),
            "instruction_count": instruction_count,
            "code_size_bytes": code_size,
            "selected": order == plan.order,
        }
        for order, instruction_count, code_size in plan.final_candidates
    ]
    totals = {
        strategy: {
            "instruction_count": sum(int(row["instruction_count"]) for row in benchmark_rows if row["strategy"] == strategy),
            "code_size_bytes": sum(int(row["code_size_bytes"]) for row in benchmark_rows if row["strategy"] == strategy),
            "compile_seconds": sum(float(row["compile_median_seconds"]) for row in benchmark_rows if row["strategy"] == strategy),
            "execution_seconds": sum(float(row["execution_median_seconds"]) for row in benchmark_rows if row["strategy"] == strategy),
        }
        for strategy in strategies
    }
    fixed_training = apply_passes(training_ir, FIXED_ORDER)
    summary = {
        "profile": profile,
        "seed": SEED,
        "environment": environment_metadata(),
        "language_semantics": {
            "grammar": "assignments and print statements; integer literals/variables; +, -, *, unary -, and parentheses",
            "arithmetic": "unbounded mathematical integers (Python int); no overflow or division",
            "evaluation": "left-to-right deterministic expression evaluation",
            "side_effects": "expressions are pure; print output is the only observable program result",
            "undefined_variables": "rejected during lowering and AST evaluation",
        },
        "passes": list(PASS_FUNCTIONS),
        "pass_order_optimization": {
            "method": "exact subset dynamic programming",
            "training_program_separate_from_benchmarks": True,
            "constraints": "apply each of four passes exactly once",
            "objective": "lexicographically minimize final instruction count, then encoded code bytes",
            "fixed_order": list(FIXED_ORDER),
            "fixed_training_score": list(_score(fixed_training)),
            "selected_order": list(plan.order),
            "selected_training_score": [plan.instruction_count, plan.code_size_bytes],
            "states_explored": plan.states_explored,
            "transitions": plan.transitions,
            "planning_seconds": planning_seconds,
        },
        "benchmark_totals": totals,
        "semantic_checks": {
            "fixture_strategy_combinations": len(equivalence_rows),
            "generated_programs": generated_checked,
            "all_equivalent": all(bool(row["equivalent"]) for row in equivalence_rows),
        },
        "full_profile_status": "DONE" if profile == "full" else "NOT RUN",
        "limitations": [
            "The language is intentionally tiny and has no input, control flow, functions, memory, or division.",
            "Only print output is observable; removing assignments that cannot reach print is therefore semantics-preserving.",
            "Pass ordering is trained on one separate synthetic program and may not generalize to other workloads.",
            "The generated bytecode is executed by a Python educational VM, so wall time mostly reflects interpreter overhead.",
            "Short compile and execution measurements vary with host load; all raw repeats are retained.",
        ],
    }

    _write_csv(output_dir / "benchmark.csv", benchmark_rows)
    _write_csv(output_dir / "benchmark_raw.csv", raw_rows)
    _write_csv(output_dir / "equivalence.csv", equivalence_rows)
    _write_csv(output_dir / "pass_effects.csv", pass_rows)
    _write_csv(output_dir / "pass_order_search.csv", search_rows)
    (output_dir / "ir_snapshots.json").write_text(json.dumps(snapshots, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "programs.json").write_text(
        json.dumps({"training": TRAINING_SOURCE.strip(), "benchmarks": {name: source.strip() for name, source in PROGRAMS.items()}}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_bar_svg(
        list(strategies),
        [float(totals[strategy]["instruction_count"]) for strategy in strategies],
        output_dir / "instruction_count.svg",
        "Track F total bytecode instructions",
    )
    write_bar_svg(
        list(strategies),
        [float(totals[strategy]["execution_seconds"]) for strategy in strategies],
        output_dir / "execution_time.svg",
        "Track F summed median execution time",
    )
    return ExperimentResult(
        track="f",
        profile=profile,
        status=RunStatus.DONE,
        method="four safe passes with exact DP pass ordering",
        objective=float(totals["dp_order"]["instruction_count"]),
        duration_seconds=perf_counter() - started,
        seed=SEED,
        message=f"wrote measured Track F artifacts to {output_dir}",
        metrics={
            "unoptimized_instructions": totals["unoptimized"]["instruction_count"],
            "fixed_order_instructions": totals["fixed_order"]["instruction_count"],
            "dp_order_instructions": totals["dp_order"]["instruction_count"],
            "generated_equivalence_checks": generated_checked,
            "all_four_passes_changed_targeted_ir": all(bool(row["changed"]) for row in pass_rows),
        },
        metadata=environment_metadata(),
    )
