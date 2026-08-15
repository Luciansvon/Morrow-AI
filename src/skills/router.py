"""Select only relevant skills setelah role dipilih."""

from src.core.types import NormalizedMessage, RoleID
from src.skills.loader import SkillDefinition
from src.skills.registry import skill_registry


class SkillRouter:
    @staticmethod
    def resolve_skills_for_task(role: RoleID, message: NormalizedMessage) -> list[SkillDefinition]:
        eligible = skill_registry.get_eligible_skills_for_role(role)
        text = message.text.lower()
        selected: list[SkillDefinition] = []
        for skill in eligible:
            if skill.name == "document_inspection":
                if message.attachments:
                    selected.append(skill)
                continue
            if not skill.triggers or any(trigger.lower() in text for trigger in skill.triggers):
                selected.append(skill)

        if not selected:
            primary_by_role = {
                RoleID.MANAGER: "task_coordination",
                RoleID.MARKETING: "campaign_strategy",
                RoleID.ADVISOR: "risk_decision_analysis",
            }
            fallback = skill_registry.get_skill(primary_by_role[role])
            if fallback:
                selected.append(fallback)
        return selected


skill_router = SkillRouter()
