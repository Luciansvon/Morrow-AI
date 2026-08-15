"""One-shot approval gateway with atomic state transitions and exact-parameter execution."""

import json
import uuid
from datetime import datetime, timedelta
from typing import Any

from src.approval.fingerprint import fingerprinter
from src.core.types import ApprovalRequest, ApprovalStatus, RoleID, utc_now
from src.storage.sqlite import db
from src.tools.builtins import ensure_builtin_tools_registered
from src.tools.executor import tool_executor
from src.tools.policy import tool_policy


class ApprovalGateway:
    @staticmethod
    async def create_request(group_id: str, action_type: str, parameters: dict[str, Any], requested_by: RoleID, duration_minutes: int = 15) -> ApprovalRequest:
        if tool_policy.classify(action_type) != "external":
            raise ValueError(f"Approval hanya boleh dibuat untuk aksi eksternal terklasifikasi: {action_type}")
        if duration_minutes <= 0:
            raise ValueError("Durasi approval harus lebih dari 0 menit.")
        approval_id = f"appr_{uuid.uuid4().hex[:12]}"
        param_hash = fingerprinter.generate_hash(action_type, parameters)
        idempotency_key = f"idem_{uuid.uuid4().hex[:16]}"
        expires_at = utc_now() + timedelta(minutes=duration_minutes)
        await db.execute("""INSERT INTO approvals (approval_id, group_id, action_type, normalized_parameters, parameter_hash, requested_by_role, idempotency_key, status, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", (approval_id, group_id, action_type, json.dumps(parameters, sort_keys=True), param_hash, requested_by.value, idempotency_key, ApprovalStatus.PENDING.value, expires_at.isoformat()))
        return ApprovalRequest(approval_id=approval_id, group_id=group_id, action_type=action_type, normalized_parameters=parameters, parameter_hash=param_hash, requested_by_role=requested_by, idempotency_key=idempotency_key, status=ApprovalStatus.PENDING, expires_at=expires_at)

    @staticmethod
    async def get_request(approval_id: str) -> dict[str, Any] | None:
        return await db.fetch_one("SELECT * FROM approvals WHERE approval_id=?", (approval_id,))

    @staticmethod
    async def approve_request(approval_id: str, approved_by: str, current_parameters: dict[str, Any] | None = None, expected_group_id: str | None = None) -> tuple[bool, str]:
        async with db.transaction() as conn:
            cursor = await conn.execute("SELECT * FROM approvals WHERE approval_id=?", (approval_id,))
            raw = await cursor.fetchone()
            if not raw:
                return False, f"Permintaan approval ID '{approval_id}' tidak ditemukan."
            row = dict(raw)
            if expected_group_id is not None and row["group_id"] != expected_group_id:
                return False, "Approval berasal dari grup yang berbeda."
            if row["status"] != ApprovalStatus.PENDING.value:
                return False, f"Permintaan approval sudah berstatus '{row['status']}'."
            if utc_now() > datetime.fromisoformat(row["expires_at"]):
                await conn.execute("UPDATE approvals SET status=? WHERE approval_id=? AND status=?", (ApprovalStatus.EXPIRED.value, approval_id, ApprovalStatus.PENDING.value))
                return False, "Permintaan approval telah kedaluwarsa."
            stored_params = json.loads(row["normalized_parameters"])
            params = stored_params if current_parameters is None else current_parameters
            if not fingerprinter.verify_hash(row["action_type"], params, row["parameter_hash"]):
                await conn.execute("UPDATE approvals SET status=? WHERE approval_id=? AND status=?", (ApprovalStatus.REJECTED.value, approval_id, ApprovalStatus.PENDING.value))
                return False, "Parameter aksi telah berubah sejak diajukan! Izin lama otomatis dibatalkan."
            updated = await conn.execute("UPDATE approvals SET status=?, approved_by=? WHERE approval_id=? AND status=?", (ApprovalStatus.APPROVED.value, approved_by, approval_id, ApprovalStatus.PENDING.value))
            if updated.rowcount != 1:
                return False, "Approval sudah diproses oleh request lain."
        return True, "Permintaan aksi luar disetujui."

    @staticmethod
    async def reject_request(approval_id: str, expected_group_id: str | None = None) -> bool:
        async with db.transaction() as conn:
            cursor = await conn.execute("SELECT group_id, status FROM approvals WHERE approval_id=?", (approval_id,))
            raw = await cursor.fetchone()
            if not raw:
                return False
            row = dict(raw)
            if expected_group_id is not None and row["group_id"] != expected_group_id:
                return False
            if row["status"] != ApprovalStatus.PENDING.value:
                return False
            updated = await conn.execute("UPDATE approvals SET status=? WHERE approval_id=? AND status=?", (ApprovalStatus.REJECTED.value, approval_id, ApprovalStatus.PENDING.value))
            return updated.rowcount == 1

    @staticmethod
    async def execute_approved_request(approval_id: str) -> dict[str, Any]:
        async with db.transaction() as conn:
            cursor = await conn.execute("SELECT * FROM approvals WHERE approval_id=?", (approval_id,))
            raw = await cursor.fetchone()
            if not raw:
                return {"success": False, "error": "APPROVAL_NOT_FOUND"}
            row = dict(raw)
            if row["status"] == ApprovalStatus.EXECUTED.value:
                return {"success": True, "idempotent_replay": True, "execution_id": row["execution_id"]}
            if row["status"] == ApprovalStatus.EXECUTING.value:
                return {"success": False, "error": "APPROVAL_ALREADY_EXECUTING", "status": "executing"}
            if row["status"] == ApprovalStatus.APPROVED.value and utc_now() > datetime.fromisoformat(row["expires_at"]):
                await conn.execute("UPDATE approvals SET status=? WHERE approval_id=? AND status=?", (ApprovalStatus.EXPIRED.value, approval_id, ApprovalStatus.APPROVED.value))
                return {"success": False, "error": "APPROVAL_EXPIRED"}
            if row["status"] != ApprovalStatus.APPROVED.value:
                return {"success": False, "error": f"APPROVAL_STATUS_{row['status'].upper()}"}
            execution_id = f"exec_{uuid.uuid4().hex[:12]}"
            claimed = await conn.execute("UPDATE approvals SET status=?, execution_id=? WHERE approval_id=? AND status=?", (ApprovalStatus.EXECUTING.value, execution_id, approval_id, ApprovalStatus.APPROVED.value))
            if claimed.rowcount != 1:
                return {"success": False, "error": "APPROVAL_EXECUTION_CLAIM_LOST"}
        ensure_builtin_tools_registered()
        params = json.loads(row["normalized_parameters"])
        result = await tool_executor.execute_tool(row["action_type"], params, idempotency_key=row["idempotency_key"], is_approved=True, approval_id=approval_id, execution_context={"group_id": row["group_id"], "role_id": row["requested_by_role"]})
        tool_execution_id = result.get("execution_id")
        if result.get("success"):
            status = ApprovalStatus.EXECUTED
            error = None
        elif result.get("status") == "unknown":
            status = ApprovalStatus.UNKNOWN
            error = result.get("error")
        else:
            status = ApprovalStatus.FAILED
            error = result.get("error")
        await db.execute("UPDATE approvals SET status=?, execution_error=? WHERE approval_id=? AND execution_id=? AND status=?", (status.value, error, approval_id, execution_id, ApprovalStatus.EXECUTING.value))
        return {**result, "tool_execution_id": tool_execution_id, "execution_id": execution_id, "approval_status": status.value}


approval_gateway = ApprovalGateway()
