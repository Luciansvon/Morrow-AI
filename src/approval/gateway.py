"""Gerbang persetujuan tindakan luar (Approval Gateway) dengan validasi parameter hash."""

import json
import uuid
from datetime import datetime, timedelta
from typing import Any

from src.approval.fingerprint import fingerprinter
from src.core.types import ApprovalRequest, ApprovalStatus, RoleID, utc_now
from src.storage.sqlite import db


class ApprovalGateway:
    """Pengelola token persetujuan aksi eksternal 1x pakai."""

    @staticmethod
    async def create_request(
        group_id: str,
        action_type: str,
        parameters: dict[str, Any],
        requested_by: RoleID,
        duration_minutes: int = 15,
    ) -> ApprovalRequest:
        approval_id = f"appr_{uuid.uuid4().hex[:10]}"
        param_hash = fingerprinter.generate_hash(action_type, parameters)
        idempotency_key = f"idem_{uuid.uuid4().hex[:12]}"
        expires_at = utc_now() + timedelta(minutes=duration_minutes)

        req = ApprovalRequest(
            approval_id=approval_id,
            action_type=action_type,
            normalized_parameters=parameters,
            parameter_hash=param_hash,
            requested_by_role=requested_by,
            idempotency_key=idempotency_key,
            status=ApprovalStatus.PENDING,
            expires_at=expires_at,
        )

        await db.execute(
            """
            INSERT INTO approvals (
                approval_id, group_id, action_type, normalized_parameters,
                parameter_hash, requested_by_role, idempotency_key, status, expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                approval_id,
                group_id,
                action_type,
                json.dumps(parameters),
                param_hash,
                requested_by.value,
                idempotency_key,
                ApprovalStatus.PENDING.value,
                expires_at.isoformat(),
            ),
        )
        return req

    @staticmethod
    async def approve_request(
        approval_id: str,
        approved_by: str,
        current_parameters: dict[str, Any],
    ) -> tuple[bool, str]:
        """
        Menyetujui permintaan aksi luar.
        Jika parameter berubah dari saat awal diminta, approval DIBATALKAN.
        """
        row = await db.fetch_one(
            "SELECT * FROM approvals WHERE approval_id = ?",
            (approval_id,),
        )
        if not row:
            return False, f"Permintaan approval ID '{approval_id}' tidak ditemukan."

        if row["status"] != ApprovalStatus.PENDING.value:
            return False, f"Permintaan approval sudah berstatus '{row['status']}'."

        expires_at = datetime.fromisoformat(row["expires_at"])
        if utc_now() > expires_at:
            await db.execute(
                "UPDATE approvals SET status = ? WHERE approval_id = ?",
                (ApprovalStatus.EXPIRED.value, approval_id),
            )
            return False, "Permintaan approval telah kedaluwarsa."

        # Verifikasi apakah parameter berubah setelah diajukan (Parameter Mutation Protection)
        initial_hash = row["parameter_hash"]
        action_type = row["action_type"]
        if not fingerprinter.verify_hash(action_type, current_parameters, initial_hash):
            await db.execute(
                "UPDATE approvals SET status = ? WHERE approval_id = ?",
                (ApprovalStatus.REJECTED.value, approval_id),
            )
            return False, "Parameter aksi telah berubah sejak diajukan! Izin lama otomatis dibatalkan."

        # Tandai disetujui (1x pakai)
        await db.execute(
            """
            UPDATE approvals
            SET status = ?, approved_by = ?
            WHERE approval_id = ?
            """,
            (ApprovalStatus.APPROVED.value, approved_by, approval_id),
        )
        return True, "Permintaan aksi luar disetujui."

    @staticmethod
    async def reject_request(approval_id: str) -> bool:
        """Menolak permintaan aksi luar."""
        await db.execute(
            "UPDATE approvals SET status = ? WHERE approval_id = ?",
            (ApprovalStatus.REJECTED.value, approval_id),
        )
        return True


approval_gateway = ApprovalGateway()
