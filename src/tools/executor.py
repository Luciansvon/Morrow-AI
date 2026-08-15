"""Durable tool executor with fail-closed policy, journaling, provenance, and idempotency."""

import json
import uuid
from typing import Any

from src.storage.sqlite import db
from src.tools.policy import tool_policy
from src.tools.provenance import provenance_for_tool
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

    @staticmethod
    def _ctx(execution_context: dict[str, Any] | None, key: str) -> Any:
        return (execution_context or {}).get(key)

    async def _journal(
        self,
        *,
        execution_id: str,
        idempotency_key: str | None,
        tool_name: str,
        parameters: dict[str, Any],
        classification: str,
        capability: str,
        policy_decision: str,
        status: str,
        side_effect: bool,
        retry_safe: bool,
        execution_context: dict[str, Any] | None,
        approval_id: str | None = None,
        result: Any = None,
        error: str | None = None,
        provenance: dict[str, Any] | None = None,
        finished: bool = False,
    ) -> None:
        await db.execute(
            """INSERT INTO tool_executions
               (execution_id, idempotency_key, group_id, thread_id, task_id, role_id,
                tool_name, parameters_json, classification, capability, policy_decision,
                approval_id, status, result_json, error_text, retry_count, side_effect,
                retry_safe, provenance_json, finished_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?,
                       CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE NULL END)""",
            (
                execution_id,
                idempotency_key,
                self._ctx(execution_context, "group_id"),
                self._ctx(execution_context, "thread_id"),
                self._ctx(execution_context, "task_id"),
                self._ctx(execution_context, "role_id"),
                tool_name,
                json.dumps(parameters, sort_keys=True, ensure_ascii=False, default=str),
                classification,
                capability,
                policy_decision,
                approval_id,
                status,
                json.dumps(result, ensure_ascii=False, default=str) if result is not None else None,
                error,
                int(side_effect),
                int(retry_safe),
                json.dumps(provenance, ensure_ascii=False, default=str) if provenance else None,
                int(finished),
            ),
        )

    async def _finish(
        self,
        execution_id: str,
        *,
        status: str,
        result: Any = None,
        error: str | None = None,
        provenance: dict[str, Any] | None = None,
    ) -> None:
        await db.execute(
            """UPDATE tool_executions
               SET status=?, result_json=?, error_text=?, provenance_json=?,
                   finished_at=CURRENT_TIMESTAMP
               WHERE execution_id=?""",
            (
                status,
                json.dumps(result, ensure_ascii=False, default=str) if result is not None else None,
                error,
                json.dumps(provenance, ensure_ascii=False, default=str) if provenance else None,
                execution_id,
            ),
        )

    async def execute_tool(
        self,
        tool_name: str,
        parameters: dict[str, Any],
        idempotency_key: str | None = None,
        is_approved: bool = False,
        *,
        approval_id: str | None = None,
        execution_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        classification = tool_policy.classify(tool_name)
        registered = tool_registry.get_registered_tool(tool_name)
        capability = registered.capability.value if registered else "unknown"
        side_effect = bool(registered.side_effect) if registered else classification == "external"
        retry_safe = bool(registered.retry_safe) if registered else classification == "internal"
        execution_id = f"exec_{uuid.uuid4().hex[:16]}"

        if idempotency_key:
            previous = await db.fetch_one(
                """SELECT execution_id, tool_name, parameters_json, status, result_json,
                          error_text, provenance_json
                   FROM tool_executions WHERE idempotency_key=?""",
                (idempotency_key,),
            )
            if previous:
                if not self._same_request(previous, tool_name, parameters):
                    return {
                        "success": False,
                        "error": "IDEMPOTENCY_KEY_CONFLICT",
                        "execution_id": previous["execution_id"],
                    }
                if previous["status"] == "succeeded":
                    return {
                        "success": True,
                        "idempotent_replay": True,
                        "execution_id": previous["execution_id"],
                        "result": (
                            json.loads(previous["result_json"])
                            if previous["result_json"]
                            else None
                        ),
                        "provenance": (
                            json.loads(previous["provenance_json"])
                            if previous.get("provenance_json")
                            else None
                        ),
                    }
                if previous["status"] in {"running", "unknown"}:
                    return {
                        "success": False,
                        "error": "EXTERNAL_RESULT_UNKNOWN_OR_IN_PROGRESS",
                        "status": previous["status"],
                        "execution_id": previous["execution_id"],
                    }
                if previous["status"] == "failed":
                    return {
                        "success": False,
                        "error": previous["error_text"] or "PREVIOUS_EXECUTION_FAILED",
                        "execution_id": previous["execution_id"],
                    }

        if classification == "unknown":
            await self._journal(
                execution_id=execution_id,
                idempotency_key=idempotency_key,
                tool_name=tool_name,
                parameters=parameters,
                classification=classification,
                capability=capability,
                policy_decision="deny_unclassified",
                status="denied",
                side_effect=side_effect,
                retry_safe=False,
                execution_context=execution_context,
                approval_id=approval_id,
                error="TOOL_POLICY_UNCLASSIFIED",
                finished=True,
            )
            return {
                "success": False,
                "error": "TOOL_POLICY_UNCLASSIFIED",
                "tool": tool_name,
                "execution_id": execution_id,
            }

        external = classification == "external"
        if external and not is_approved:
            await self._journal(
                execution_id=execution_id,
                idempotency_key=idempotency_key,
                tool_name=tool_name,
                parameters=parameters,
                classification=classification,
                capability=capability,
                policy_decision="approval_required",
                status="approval_required",
                side_effect=True,
                retry_safe=False,
                execution_context=execution_context,
                approval_id=approval_id,
                error="APPROVAL_REQUIRED",
                finished=True,
            )
            return {
                "success": False,
                "error": f"Aksi eksternal '{tool_name}' membutuhkan persetujuan eksplisit pengguna.",
                "requires_approval": True,
                "execution_id": execution_id,
            }
        if external and not idempotency_key:
            await self._journal(
                execution_id=execution_id,
                idempotency_key=None,
                tool_name=tool_name,
                parameters=parameters,
                classification=classification,
                capability=capability,
                policy_decision="deny_missing_idempotency",
                status="denied",
                side_effect=True,
                retry_safe=False,
                execution_context=execution_context,
                approval_id=approval_id,
                error="IDEMPOTENCY_KEY_REQUIRED",
                finished=True,
            )
            return {
                "success": False,
                "error": "IDEMPOTENCY_KEY_REQUIRED",
                "execution_id": execution_id,
            }

        func = tool_registry.get_tool(tool_name)
        if not func:
            await self._journal(
                execution_id=execution_id,
                idempotency_key=idempotency_key,
                tool_name=tool_name,
                parameters=parameters,
                classification=classification,
                capability=capability,
                policy_decision="deny_not_registered",
                status="denied",
                side_effect=side_effect,
                retry_safe=False,
                execution_context=execution_context,
                approval_id=approval_id,
                error="TOOL_NOT_REGISTERED",
                finished=True,
            )
            return {
                "success": False,
                "error": "TOOL_NOT_REGISTERED",
                "tool": tool_name,
                "execution_id": execution_id,
            }

        try:
            await self._journal(
                execution_id=execution_id,
                idempotency_key=idempotency_key,
                tool_name=tool_name,
                parameters=parameters,
                classification=classification,
                capability=capability,
                policy_decision="allow",
                status="running",
                side_effect=side_effect,
                retry_safe=retry_safe,
                execution_context=execution_context,
                approval_id=approval_id,
            )
        except Exception:
            if idempotency_key:
                previous = await db.fetch_one(
                    "SELECT * FROM tool_executions WHERE idempotency_key=?",
                    (idempotency_key,),
                )
                if previous:
                    return await self.execute_tool(
                        tool_name,
                        parameters,
                        idempotency_key=idempotency_key,
                        is_approved=is_approved,
                        approval_id=approval_id,
                        execution_context=execution_context,
                    )
            raise

        output_trust = registered.output_trust if registered else "untrusted"
        observation_provenance = provenance_for_tool(
            tool_name,
            output_trust,
            details={
                "classification": classification,
                "capability": capability,
            },
        ).to_dict()

        try:
            result = await func(**parameters)
            await self._finish(
                execution_id,
                status="succeeded",
                result=result,
                provenance=observation_provenance,
            )
            return {
                "success": True,
                "execution_id": execution_id,
                "result": result,
                "provenance": observation_provenance,
                "retry_allowed": retry_safe,
            }
        except UnknownExternalResultError as exc:
            await self._finish(
                execution_id,
                status="unknown",
                error=str(exc),
                provenance=observation_provenance,
            )
            return {
                "success": False,
                "execution_id": execution_id,
                "error": str(exc),
                "status": "unknown",
                "retry_allowed": False,
                "provenance": observation_provenance,
            }
        except Exception as exc:
            await self._finish(
                execution_id,
                status="failed",
                error=str(exc),
                provenance=observation_provenance,
            )
            return {
                "success": False,
                "execution_id": execution_id,
                "error": str(exc),
                "retry_allowed": retry_safe and not side_effect,
                "provenance": observation_provenance,
            }


tool_executor = IdempotentToolExecutor()
