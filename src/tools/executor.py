"""Durable tool executor with fail-closed policy and strong idempotency binding."""

import json
from typing import Any

from src.storage.sqlite import db
from src.tools.policy import tool_policy
from src.tools.registry import tool_registry


class UnknownExternalResultError(RuntimeError):
    """Side effect may have happened, but the provider result is indeterminate."""


class IdempotentToolExecutor:
    @staticmethod
    def _same_request(previous: dict[str, Any], tool_name: str, parameters: dict[str, Any]) -> bool:
        if previous["tool_name"] != tool_name:
            return False
        try:
            stored = json.loads(previous["parameters_json"])
        except (TypeError, json.JSONDecodeError):
            return False
        return stored == parameters

    async def execute_tool(
        self,
        tool_name: str,
        parameters: dict[str, Any],
        idempotency_key: str | None = None,
        is_approved: bool = False,
    ) -> dict[str, Any]:
        classification = tool_policy.classify(tool_name)
        if classification == "unknown":
            return {
                "success": False,
                "error": "TOOL_POLICY_UNCLASSIFIED",
                "tool": tool_name,
            }

        external = classification == "external"
        if external and not is_approved:
            return {
                "success": False,
                "error": f"Aksi eksternal '{tool_name}' membutuhkan persetujuan eksplisit pengguna.",
                "requires_approval": True,
            }
        if external and not idempotency_key:
            return {"success": False, "error": "IDEMPOTENCY_KEY_REQUIRED"}

        if idempotency_key:
            previous = await db.fetch_one(
                """SELECT tool_name, parameters_json, status, result_json, error_text
                   FROM tool_executions WHERE idempotency_key=?""",
                (idempotency_key,),
            )
            if previous:
                if not self._same_request(previous, tool_name, parameters):
                    return {"success": False, "error": "IDEMPOTENCY_KEY_CONFLICT"}
                if previous["status"] == "succeeded":
                    return {
                        "success": True,
                        "idempotent_replay": True,
                        "result": (
                            json.loads(previous["result_json"])
                            if previous["result_json"]
                            else None
                        ),
                    }
                if previous["status"] in {"running", "unknown"}:
                    return {
                        "success": False,
                        "error": "EXTERNAL_RESULT_UNKNOWN_OR_IN_PROGRESS",
                        "status": previous["status"],
                    }
                if previous["status"] == "failed":
                    return {
                        "success": False,
                        "error": previous["error_text"] or "PREVIOUS_EXECUTION_FAILED",
                    }

        func = tool_registry.get_tool(tool_name)
        if not func:
            return {"success": False, "error": "TOOL_NOT_REGISTERED", "tool": tool_name}

        if idempotency_key:
            canonical = json.dumps(parameters, sort_keys=True)
            cursor = await db.execute(
                """INSERT OR IGNORE INTO tool_executions
                   (idempotency_key, tool_name, parameters_json, status)
                   VALUES (?, ?, ?, 'running')""",
                (idempotency_key, tool_name, canonical),
            )
            if cursor.rowcount != 1:
                return await self.execute_tool(
                    tool_name,
                    parameters,
                    idempotency_key=idempotency_key,
                    is_approved=is_approved,
                )

        try:
            result = await func(**parameters)
            if idempotency_key:
                await db.execute(
                    """UPDATE tool_executions
                       SET status='succeeded', result_json=?, finished_at=CURRENT_TIMESTAMP
                       WHERE idempotency_key=? AND status='running'""",
                    (json.dumps(result, default=str), idempotency_key),
                )
            return {"success": True, "result": result}
        except UnknownExternalResultError as exc:
            if idempotency_key:
                await db.execute(
                    """UPDATE tool_executions
                       SET status='unknown', error_text=?, finished_at=CURRENT_TIMESTAMP
                       WHERE idempotency_key=? AND status='running'""",
                    (str(exc), idempotency_key),
                )
            return {
                "success": False,
                "error": str(exc),
                "status": "unknown",
                "retry_allowed": False,
            }
        except Exception as exc:
            if idempotency_key:
                await db.execute(
                    """UPDATE tool_executions
                       SET status='failed', error_text=?, finished_at=CURRENT_TIMESTAMP
                       WHERE idempotency_key=? AND status='running'""",
                    (str(exc), idempotency_key),
                )
            return {"success": False, "error": str(exc)}


tool_executor = IdempotentToolExecutor()
