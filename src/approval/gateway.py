"""One-shot approval gateway dengan exact-parameter execution."""

import json
import uuid
from datetime import datetime, timedelta
from typing import Any

from src.approval.fingerprint import fingerprinter
from src.core.types import ApprovalRequest, ApprovalStatus, RoleID, utc_now
from src.storage.sqlite import db
from src.tools.executor import tool_executor


class ApprovalGateway:
    @staticmethod
    async def create_request(
        group_id: str,
        action_type: str,
        parameters: dict[str, Any],
        requested_by: RoleID,
        duration_minutes: int = 15,
    ) -> ApprovalRequest:
        approval_id = f"appr_{uuid.uuid4().hex[:12]}"
        param_hash = fingerprinter.generate_hash(action_type, parameters)
        idempotency_key = f"idem_{uuid.uuid4().hex[:16]}"
        expires_at = utc_now() + timedelta(minutes=duration_minutes)
        await db.execute(
            """INSERT INTO approvals
               (approval_id, group_id, action_type, normalized_parameters, parameter_hash,
                requested_by_role, idempotency_key, status, expires_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                approval_id, group_id, action_type, json.dumps(parameters, sort_keys=True),
                param_hash, requested_by.value, idempotency_key,
                ApprovalStatus.PENDING.value, expires_at.isoformat(),
            ),
        )
        return ApprovalRequest(
            approval_id=approval_id, group_id=group_id, action_type=action_type,
            normalized_parameters=parameters, parameter_hash=param_hash,
            requested_by_role=requested_by, idempotency_key=idempotency_key,
            status=ApprovalStatus.PENDING, expires_at=expires_at,
        )

    @staticmethod
    async def get_request(approval_id: str) -> dict[str, Any] | None:
        return await db.fetch_one("SELECT * FROM approvals WHERE approval_id=?", (approval_id,))

    @staticmethod
    async def approve_request(
        approval_id: str,
        approved_by: str,
        current_parameters: dict[str, Any] | None = None,
        expected_group_id: str | None = None,
    ) -> tuple[bool, str]:
        row = await ApprovalGateway.get_request(approval_id)
        if not row:
            return False, f"Permintaan approval ID '{approval_id}' tidak ditemukan."
        if expected_group_id is not None and row["group_id"] != expected_group_id:
            return False, "Approval berasal dari grup yang berbeda."
        if row["status"] != ApprovalStatus.PENDING.value:
            return False, f"Permintaan approval sudah berstatus '{row['status']}'."
        if utc_now() > datetime.fromisoformat(row["expires_at"]):
            await db.execute("UPDATE approvals SET status=? WHERE approval_id=?", (ApprovalStatus.EXPIRED.value, approval_id))
            return False, "Permintaan approval telah kedaluwarsa."

        stored_params = json.loads(row["normalized_parameters"])
        params = stored_params if current_parameters is None else current_parameters
        if not fingerprinter.verify_hash(row["action_type"], params, row["parameter_hash"]):
            await db.execute("UPDATE approvals SET status=? WHERE approval_id=?", (ApprovalStatus.REJECTED.value, approval_id))
            return False, "Parameter aksi telah berubah sejak diajukan! Izin lama otomatis dibatalkan."
        await db.execute(
            "UPDATE approvals SET status=?, approved_by=? WHERE approval_id=?",
            (ApprovalStatus.APPROVED.value, approved_by, approval_id),
        )
        return True, "Permintaan aksi luar disetujui."

    @staticmethod
    async def reject_request(approval_id: str, expected_group_id: str | None = None) -> bool:
        row = await ApprovalGateway.get_request(approval_id)
        if not row or (expected_group_id is not None and row["group_id"] != expected_group_id):
            return False
        if row["status"] != ApprovalStatus.PENDING.value:
            return False
        await db.execute("UPDATE approvals SET status=? WHERE approval_id=?", (ApprovalStatus.REJECTED.value, approval_id))
        return True

    @staticmethod
    async def execute_approved_request(approval_id: str) -> dict[str, Any]:
        row = await ApprovalGateway.get_request(approval_id)
        if not row:
            return {"success": False, "error": "APPROVAL_NOT_FOUND"}
        if row["status"] == ApprovalStatus.EXECUTED.value:
            return {"success": True, "idempotent_replay": True, "execution_id": row["execution_id"]}
        if row["status"] != ApprovalStatus.APPROVED.value:
            return {"success": False, "error": f"APPROVAL_STATUS_{row['status'].upper()}"}

        execution_id = f"exec_{uuid.uuid4().hex[:12]}"
        await db.execute(
            "UPDATE approvals SET status=?, execution_id=? WHERE approval_id=? AND status=?",
            (ApprovalStatus.EXECUTING.value, execution_id, approval_id, ApprovalStatus.APPROVED.value),
        )
        params = json.loads(row["normalized_parameters"])
        result = await tool_executor.execute_tool(
            row["action_type"], params, idempotency_key=row["idempotency_key"], is_approved=True,
        )
        if result.get("success"):
            status = ApprovalStatus.EXECUTED
            error = None
        elif result.get("status") == "unknown":
            status = ApprovalStatus.UNKNOWN
            error = result.get("error")
        else:
            status = ApprovalStatus.FAILED
            error = result.get("error")
        await db.execute(
            "UPDATE approvals SET status=?, execution_error=? WHERE approval_id=?",
            (status.value, error, approval_id),
        )
        return {**result, "execution_id": execution_id, "approval_status": status.value}


approval_gateway = ApprovalGateway()
