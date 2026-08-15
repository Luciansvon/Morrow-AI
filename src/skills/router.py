"""Penyalur keahlian (Skill Router) setelah identitas peran ditetapkan."""

from src.core.types import NormalizedMessage, RoleID
from src.skills.loader import SkillDefinition
from src.skills.registry import skill_registry


class SkillRouter:
    """Menentukan kumpulan instruksi skill relevan untuk agen yang sedang bertugas."""

    @staticmethod
    def resolve_skills_for_task(role: RoleID, message: NormalizedMessage) -> list[SkillDefinition]:
        eligible = skill_registry.get_eligible_skills_for_role(role)
        # Untuk MVP, sertakan seluruh skill yang memenuhi syarat peran
        return eligible


skill_router = SkillRouter()
