from __future__ import annotations

import ast
import operator
import re
from dataclasses import dataclass
from typing import Optional, Union

Number = Union[int, float]

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

_EXPR_RE = re.compile(
    r"^\s*[\(\+\-]*\d[\d\s\+\-\*/%\^\.\(\)]*(=\s*[\d\.]*)?\s*$"
)
_INCOMPLETE_RE = re.compile(r"=\s*$")
_IS_EQ_RE = re.compile(
    r"^\s*(?:is\s+)?(.+?)\s*(?:=|equals|equal to)\s*(.+?)\??\s*$",
    re.IGNORECASE,
)


class MathError(Exception):
    pass


class IncompleteExpression(MathError):
    pass


def looks_like_math(text: str) -> bool:
    cleaned = text.strip().rstrip("?").strip()
    if not cleaned:
        return False
    lowered = cleaned.lower()
    if lowered.startswith(("is ", "does ", "calculate ", "compute ", "what is ")):
        candidate = re.sub(
            r"^(is|does|calculate|compute|what is)\s+",
            "",
            lowered,
            flags=re.IGNORECASE,
        )
        candidate = candidate.replace("equal to", "=").replace("equals", "=")
        return bool(_EXPR_RE.match(candidate.replace("^", "**")))
    return bool(_EXPR_RE.match(cleaned.replace("^", "**")))


def is_incomplete_expression(text: str) -> bool:
    cleaned = text.strip()
    if not _INCOMPLETE_RE.search(cleaned):
        return False
    left = cleaned.rsplit("=", 1)[0].strip()
    return bool(left) and bool(_EXPR_RE.match(left.replace("^", "**") + " 1"))


def _eval_node(node: ast.AST) -> Number:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.operand))  # type: ignore[operator]
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)) and right == 0:
            raise MathError("Division by zero")
        result = _OPS[type(node.op)](left, right)
        if isinstance(result, complex):
            raise MathError("Complex results are not supported")
        return result
    raise MathError("Unsupported expression")


def evaluate_expression(expression: str) -> Number:
    expr = expression.strip().replace("^", "**")
    if is_incomplete_expression(expr):
        raise IncompleteExpression("Incomplete mathematical expression")
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        raise MathError("Invalid mathematical expression") from exc
    for node in ast.walk(tree):
        if isinstance(node, (ast.Call, ast.Attribute, ast.Name, ast.Subscript, ast.List, ast.Dict)):
            raise MathError("Unsupported mathematical expression")
    return _eval_node(tree)


@dataclass
class MathResult:
    expression: str
    value: Optional[Number]
    comparison: Optional[bool] = None
    incomplete: bool = False
    error: Optional[str] = None

    @property
    def display(self) -> str:
        if self.incomplete:
            return (
                "That looks like an incomplete expression. "
                "Add the rest of the equation if you want it evaluated."
            )
        if self.error:
            return self.error
        if self.comparison is not None:
            expected = "true" if self.comparison else "false"
            return f"{self.expression} is {expected}. The calculated value of the left side matches the right side: {self.comparison}."
        return str(self.value)


def parse_math_query(text: str) -> MathResult:
    raw = text.strip()
    if is_incomplete_expression(raw):
        return MathResult(expression=raw, value=None, incomplete=True)

    lowered = raw.lower().strip().rstrip("?")
    lowered = re.sub(r"^(is|does|calculate|compute|what is|what's|whats)\s+", "", lowered)
    lowered = lowered.replace("equal to", "=").replace("equals", "=")

    if "=" in lowered:
        left, right = lowered.split("=", 1)
        left, right = left.strip(), right.strip()
        if not right:
            return MathResult(expression=raw, value=None, incomplete=True)
        try:
            lv = evaluate_expression(left)
            rv = evaluate_expression(right)
        except MathError as exc:
            return MathResult(expression=raw, value=None, error=str(exc))
        equal = abs(float(lv) - float(rv)) < 1e-9
        return MathResult(expression=f"{left} = {right}", value=lv, comparison=equal)

    try:
        value = evaluate_expression(lowered)
        return MathResult(expression=lowered, value=value)
    except MathError as exc:
        return MathResult(expression=raw, value=None, error=str(exc))
