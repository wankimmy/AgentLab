import ast
import math
import operator
from collections.abc import Callable
from typing import Any

ALLOWED_BINOPS: dict[type, Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
ALLOWED_UNARYOPS: dict[type, Callable[[float], float]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}
ALLOWED_FUNCS: dict[str, Callable[..., float]] = {
    "sqrt": math.sqrt,
    "abs": abs,
    "round": round,
}


class CalculatorError(ValueError):
    pass


def _eval_node(node: ast.AST) -> Any:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in ALLOWED_BINOPS:
        left = float(_eval_node(node.left))
        right = float(_eval_node(node.right))
        return ALLOWED_BINOPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in ALLOWED_UNARYOPS:
        return ALLOWED_UNARYOPS[type(node.op)](float(_eval_node(node.operand)))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        func_name = node.func.id
        if func_name not in ALLOWED_FUNCS:
            raise CalculatorError(f"Function not allowed: {func_name}")
        if node.keywords:
            raise CalculatorError("Keyword arguments not allowed")
        args = [float(_eval_node(arg)) for arg in node.args]
        return float(ALLOWED_FUNCS[func_name](*args))
    raise CalculatorError("Unsupported expression")


def evaluate_expression(expression: str) -> float:
    expr = expression.strip()
    if not expr:
        raise CalculatorError("Empty expression")
    if len(expr) > 500:
        raise CalculatorError("Expression too long")
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        raise CalculatorError(f"Invalid syntax: {exc.msg}") from exc
    result = float(_eval_node(tree))
    if not math.isfinite(result):
        raise CalculatorError("Result is not finite")
    return result
