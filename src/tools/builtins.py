"""Safe local tools that do not cause external side effects."""

import ast
import math
import operator
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src.core.config import settings
from src.tools.registry import ToolCapability, tool_registry

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

_WEEKDAYS_ID = (
    "Senin",
    "Selasa",
    "Rabu",
    "Kamis",
    "Jumat",
    "Sabtu",
    "Minggu",
)
_TIMEZONE_ALIASES = {
    "jakarta": "Asia/Jakarta",
    "jakarta, indonesia": "Asia/Jakarta",
    "indonesia/jakarta": "Asia/Jakarta",
    "wib": "Asia/Jakarta",
    "utc+7": "Asia/Jakarta",
    "utc+07:00": "Asia/Jakarta",
}


def _normalize_timezone_name(timezone: str | None) -> str:
    raw = (timezone or settings.morrow_timezone).strip()
    return _TIMEZONE_ALIASES.get(raw.lower(), raw)


async def current_datetime(timezone: str | None = None) -> dict[str, str | int]:
    """Return deterministic current local date/time fields for an IANA timezone."""
    tz_name = _normalize_timezone_name(timezone)
    try:
        tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Timezone IANA tidak valid: {tz_name}") from exc
    now = datetime.now(tz)
    return {
        "timezone": tz_name,
        "iso": now.isoformat(timespec="seconds"),
        "date": now.date().isoformat(),
        "time": now.strftime("%H:%M:%S"),
        "weekday": _WEEKDAYS_ID[now.weekday()],
        "weekday_index": now.weekday(),
        "utc_offset": now.strftime("%z"),
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
    if settings.datetime_tool_enabled and tool_registry.get_tool("current_datetime") is None:
        tool_registry.register_tool(
            "current_datetime",
            current_datetime,
            description=(
                "Ambil tanggal, jam, nama hari, timezone, dan UTC offset saat ini secara deterministik. "
                "Timezone umum seperti Jakarta/WIB dinormalisasi ke Asia/Jakarta. "
                "Gunakan hasil field tool apa adanya; jangan menghitung ulang nama hari di model."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "Timezone IANA atau alias umum seperti Jakarta/WIB. Default mengikuti MORROW_TIMEZONE.",
                    }
                },
                "additionalProperties": False,
            },
            domain="utility",
            capability=ToolCapability.READ,
            risk="low",
            side_effect=False,
            output_trust="trusted_internal",
            cost_class="local",
            retry_safe=True,
            keywords={"waktu", "jam", "tanggal", "hari", "sekarang", "time", "date", "datetime", "timezone", "jakarta", "wib"},
        )

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
            domain="utility",
            capability=ToolCapability.READ,
            risk="low",
            side_effect=False,
            output_trust="trusted_internal",
            cost_class="local",
            retry_safe=True,
            keywords={"math", "calculate", "calculator", "hitung", "aritmetika", "angka", "numeric"},
        )

    if settings.tool_discovery_enabled:
        from src.tools.discovery import ensure_discovery_tool_registered

        ensure_discovery_tool_registered()

    if settings.browser_enabled:
        from src.browser.tools import ensure_browser_tools_registered

        ensure_browser_tools_registered()

    if settings.openviking_enabled or settings.immich_enabled:
        from src.integrations.tools import ensure_integration_tools_registered

        ensure_integration_tools_registered()
