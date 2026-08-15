"""Resolusi kebijakan model berbasis beban kerja (WORKLOAD = MODEL)."""


from src.core.types import ModalityType, RiskLevel, RoleID, WorkloadType
from src.llm.model_catalog import MODEL_CATALOG


class ModelPolicy:
    """Mesin pemetaan dinamis dari karakteristik tugas ke model AI yang paling hemat dan tepat."""

    @classmethod
    def resolve(
        cls,
        role: RoleID,
        workload: WorkloadType = WorkloadType.ROUTINE,
        risk_level: RiskLevel = RiskLevel.LOW,
        modality: ModalityType = ModalityType.TEXT,
    ) -> tuple[str, str]:
        """
        Mengembalikan (model_id, reasoning_effort).
        reasoning_effort: 'off', 'low', 'high', 'xhigh'
        """
        # 1. Kasus Multimodal (Gambar/Media)
        if modality == ModalityType.MULTIMODAL:
            if risk_level in (RiskLevel.HIGH, RiskLevel.EXTREME):
                return MODEL_CATALOG["minimax_m3"].model_id, "off"
            return MODEL_CATALOG["mimo_v2_5"].model_id, "off"

        # 2. Kasus Khusus Advisor (Penasihat Keputusan)
        if role == RoleID.ADVISOR:
            # Jika risiko tinggi / kritis (multiple tradeoffs & irreversible)
            if risk_level in (RiskLevel.HIGH, RiskLevel.EXTREME) or workload == WorkloadType.CRITICAL:
                return MODEL_CATALOG["deepseek_v4_pro"].model_id, "xhigh"
            # Advisor normal
            return MODEL_CATALOG["deepseek_v4_flash"].model_id, "high"

        # 3. Kasus Khusus Manager (Koordinator)
        if role == RoleID.MANAGER:
            if workload == WorkloadType.CASUAL:
                return MODEL_CATALOG["mimo_v2_5"].model_id, "off"
            elif workload == WorkloadType.ROUTINE:
                return MODEL_CATALOG["deepseek_v4_flash"].model_id, "low"
            elif workload == WorkloadType.PLANNING:
                return MODEL_CATALOG["deepseek_v4_flash"].model_id, "high"
            elif workload == WorkloadType.COMPLEX_PLANNING:
                return MODEL_CATALOG["deepseek_v4_flash"].model_id, "xhigh"
            elif workload == WorkloadType.CRITICAL:
                return MODEL_CATALOG["deepseek_v4_pro"].model_id, "high"

        # 4. Kasus Khusus Marketing (Pemasaran & Konten)
        if role == RoleID.MARKETING:
            if risk_level in (RiskLevel.HIGH, RiskLevel.EXTREME):
                return MODEL_CATALOG["minimax_m3"].model_id, "off"
            return MODEL_CATALOG["mimo_v2_5"].model_id, "off"

        # Default fallback
        return MODEL_CATALOG["deepseek_v4_flash"].model_id, "low"


model_policy = ModelPolicy()
