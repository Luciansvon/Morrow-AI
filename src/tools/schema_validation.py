"""Small deterministic JSON-Schema subset used at the tool execution boundary.

Morrow controls the schemas registered for tools, so the executor only needs the subset emitted by
our registry: object/property constraints, required fields, scalar types, enum, string patterns,
and numeric/array bounds. Unsupported schema keywords fail closed instead of being silently ignored.
"""

from __future__ import annotations

import re
from typing import Any


class ToolParametersValidationError(ValueError):
    """Tool arguments violate the registered public schema."""


_SUPPORTED_SCHEMA_KEYS = {
    "type",
    "properties",
    "required",
    "additionalProperties",
    "description",
    "enum",
    "minLength",
    "maxLength",
    "pattern",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "minItems",
    "maxItems",
    "items",
    "format",
    "default",
}


def _path(parent: str, child: str) -> str:
    return child if not parent else f"{parent}.{child}"


def _check_supported(schema: dict[str, Any], path: str) -> None:
    unsupported = set(schema) - _SUPPORTED_SCHEMA_KEYS
    if unsupported:
        labels = ", ".join(sorted(unsupported))
        raise ToolParametersValidationError(
            f"Schema tool memakai keyword yang belum didukung pada {path or '$'}: {labels}"
        )


def _validate_type(value: Any, expected: str, path: str) -> None:
    valid = {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }.get(expected)
    if valid is None:
        raise ToolParametersValidationError(f"Tipe schema tidak didukung pada {path}: {expected}")
    if not valid:
        raise ToolParametersValidationError(f"{path} harus bertipe {expected}")


def _validate(value: Any, schema: dict[str, Any], path: str = "$") -> None:
    _check_supported(schema, path)
    expected = schema.get("type")
    if expected is not None:
        if not isinstance(expected, str):
            raise ToolParametersValidationError(f"Schema type pada {path} harus string tunggal")
        _validate_type(value, expected, path)

    if "enum" in schema and value not in schema["enum"]:
        raise ToolParametersValidationError(f"{path} harus salah satu dari {schema['enum']!r}")

    if isinstance(value, dict):
        properties = schema.get("properties") or {}
        if not isinstance(properties, dict):
            raise ToolParametersValidationError(f"properties pada {path} harus object")
        required = schema.get("required") or []
        if not isinstance(required, list) or not all(isinstance(item, str) for item in required):
            raise ToolParametersValidationError(f"required pada {path} harus list string")
        missing = [key for key in required if key not in value]
        if missing:
            raise ToolParametersValidationError(
                f"{path} kehilangan parameter wajib: {', '.join(missing)}"
            )
        additional = schema.get("additionalProperties", True)
        if additional is False:
            unknown = sorted(set(value) - set(properties))
            if unknown:
                raise ToolParametersValidationError(
                    f"{path} memiliki parameter tak dikenal: {', '.join(unknown)}"
                )
        elif additional is not True and not isinstance(additional, dict):
            raise ToolParametersValidationError(
                f"additionalProperties pada {path} harus boolean atau schema object"
            )
        for key, item in value.items():
            child_schema = properties.get(key)
            if child_schema is None and isinstance(additional, dict):
                child_schema = additional
            if child_schema is not None:
                if not isinstance(child_schema, dict):
                    raise ToolParametersValidationError(
                        f"Schema property {_path(path, key)} harus object"
                    )
                _validate(item, child_schema, _path(path, key))

    if isinstance(value, str):
        if "minLength" in schema and len(value) < int(schema["minLength"]):
            raise ToolParametersValidationError(
                f"{path} minimal {int(schema['minLength'])} karakter"
            )
        if "maxLength" in schema and len(value) > int(schema["maxLength"]):
            raise ToolParametersValidationError(
                f"{path} maksimal {int(schema['maxLength'])} karakter"
            )
        if "pattern" in schema:
            try:
                matched = re.search(str(schema["pattern"]), value)
            except re.error as exc:
                raise ToolParametersValidationError(
                    f"Pattern schema invalid pada {path}: {exc}"
                ) from exc
            if matched is None:
                raise ToolParametersValidationError(f"{path} tidak cocok dengan pattern schema")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise ToolParametersValidationError(f"{path} minimal {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            raise ToolParametersValidationError(f"{path} maksimal {schema['maximum']}")
        if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
            raise ToolParametersValidationError(
                f"{path} harus lebih besar dari {schema['exclusiveMinimum']}"
            )
        if "exclusiveMaximum" in schema and value >= schema["exclusiveMaximum"]:
            raise ToolParametersValidationError(
                f"{path} harus lebih kecil dari {schema['exclusiveMaximum']}"
            )

    if isinstance(value, list):
        if "minItems" in schema and len(value) < int(schema["minItems"]):
            raise ToolParametersValidationError(f"{path} terlalu sedikit item")
        if "maxItems" in schema and len(value) > int(schema["maxItems"]):
            raise ToolParametersValidationError(f"{path} terlalu banyak item")
        item_schema = schema.get("items")
        if item_schema is not None:
            if not isinstance(item_schema, dict):
                raise ToolParametersValidationError(f"items schema pada {path} harus object")
            for index, item in enumerate(value):
                _validate(item, item_schema, f"{path}[{index}]")


def validate_tool_parameters(parameters: dict[str, Any], schema: dict[str, Any]) -> None:
    """Validate tool arguments or raise `ToolParametersValidationError`."""
    if not isinstance(parameters, dict):
        raise ToolParametersValidationError("Parameter tool harus object JSON")
    if not isinstance(schema, dict):
        raise ToolParametersValidationError("Schema tool harus object JSON")
    _validate(parameters, schema)
