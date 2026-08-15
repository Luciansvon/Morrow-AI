"""Safe local tools that do not cause external side effects."""

import ast
import math
import operator
from typing import Any

from src.tools.registry import tool_registry

_BIN_OPS: dict[type[ast.operator], Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS: dict[type[ast.unaryop], Any] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _eval_node(node: ast.AST, depth: int = 0) -> int | float:
    if depth > 24:
        raise ValueError("Ekspresi terlalu kompleks.")
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, depth + 1)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval_node(node.operand, depth + 1))
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        left = _eval_node(node.left, depth + 1)
        right = _eval_node(node.right, depth + 1)
        if isinstance(node.op, ast.Pow) and abs(right) > 12:
            raise ValueError("Eksponen terlalu besar.")
        result = _BIN_OPS[type(node.op)](left, right)
        if not math.isfinite(float(result)) or abs(float(result)) > 1e18:
            raise ValueError("Hasil di luar batas aman kalkulator.")
        return result
    raise ValueError("Ekspresi hanya boleh berisi angka dan operator aritmetika dasar.")


async def calculate(expression: str) -> dict[str, int | float | str]:
    """Evaluate arithmetic without eval(), imports, names, or arbitrary code execution."""
    if not expression or len(expression) > 500:
        raise ValueError("Ekspresi kosong atau terlalu panjang.")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError("Ekspresi matematika tidak valid.") from exc
    result = _eval_node(tree)
    return {"expression": expression, "result": result}


def ensure_builtin_tools_registered() -> None:
    if tool_registry.get_tool("calculate") is None:
        tool_registry.register_tool(
            "calculate",
            calculate,
            description=(
                "Hitung ekspresi aritmetika secara deterministik. Gunakan untuk perhitungan numerik "
                "daripada menghitung manual di dalam jawaban."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Ekspresi aritmetika, contoh: (12500 * 3) + 4500",
                    }
                },
                "required": ["expression"],
                "additionalProperties": False,
            },
        )
