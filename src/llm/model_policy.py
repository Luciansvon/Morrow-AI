"""Pemilihan model berdasarkan role, workload, risk, dan modality."""

from src.core.types import ModalityType, RiskLevel, RoleID, WorkloadType
from src.llm.model_catalog import MODEL_CATALOG


class ModelPolicy:
    @classmethod
    def resolve(
        cls,
        role: RoleID,
        workload: WorkloadType = WorkloadType.ROUTINE,
        risk_level: RiskLevel = RiskLevel.LOW,
        modality: ModalityType = ModalityType.TEXT,
    ) -> tuple[str, str]:
        if modality == ModalityType.MULTIMODAL:
            if risk_level in (RiskLevel.HIGH, RiskLevel.EXTREME) or workload in (
                WorkloadType.COMPLEX_PLANNING,
                WorkloadType.CRITICAL,
            ):
                return MODEL_CATALOG["minimax_m3"].model_id, "off"
            return MODEL_CATALOG["mimo_v2_5"].model_id, "off"

        if role == RoleID.ADVISOR:
            if risk_level in (RiskLevel.HIGH, RiskLevel.EXTREME) or workload == WorkloadType.CRITICAL:
                return MODEL_CATALOG["deepseek_v4_pro"].model_id, "xhigh"
            return MODEL_CATALOG["deepseek_v4_flash"].model_id, "high"

        if role == RoleID.MANAGER:
            if workload == WorkloadType.CASUAL:
                return MODEL_CATALOG["mimo_v2_5"].model_id, "off"
            if workload == WorkloadType.ROUTINE:
                return MODEL_CATALOG["deepseek_v4_flash"].model_id, "off"
            if workload == WorkloadType.PLANNING:
                return MODEL_CATALOG["deepseek_v4_flash"].model_id, "high"
            if workload == WorkloadType.COMPLEX_PLANNING:
                return MODEL_CATALOG["deepseek_v4_flash"].model_id, "xhigh"
            if workload == WorkloadType.CRITICAL:
                return MODEL_CATALOG["deepseek_v4_pro"].model_id, "xhigh"

        if role == RoleID.MARKETING:
            if risk_level in (RiskLevel.HIGH, RiskLevel.EXTREME) or workload in (
                WorkloadType.COMPLEX_PLANNING,
                WorkloadType.CRITICAL,
            ):
                return MODEL_CATALOG["minimax_m3"].model_id, "off"
            return MODEL_CATALOG["mimo_v2_5"].model_id, "off"

        return MODEL_CATALOG["deepseek_v4_flash"].model_id, "off"


model_policy = ModelPolicy()
