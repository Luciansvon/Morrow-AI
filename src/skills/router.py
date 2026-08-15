"""Pilih skill relevan setelah role owner sudah ditentukan."""

from typing import ClassVar

from src.core.types import NormalizedMessage, RoleID
from src.skills.loader import SkillDefinition
from src.skills.registry import skill_registry


class SkillRouter:
    MAX_MATCHED_SKILLS = 3
    PRIMARY_BY_ROLE: ClassVar[dict[RoleID, str]] = {
        RoleID.MANAGER: "task_coordination",
        RoleID.MARKETING: "campaign_strategy",
        RoleID.ADVISOR: "risk_decision_analysis",
    }

    @staticmethod
    def _match_score(skill: SkillDefinition, text: str) -> tuple[int, int]:
        matches = [trigger.lower() for trigger in skill.triggers if trigger.lower() in text]
        return len(matches), max((len(trigger) for trigger in matches), default=0)

    @classmethod
    def resolve_skills_for_task(cls, role: RoleID, message: NormalizedMessage) -> list[SkillDefinition]:
        eligible = skill_registry.get_eligible_skills_for_role(role)
        text = message.text.lower()
        attachment_skill: SkillDefinition | None = None
        matched: list[tuple[int, int, SkillDefinition]] = []

        for skill in eligible:
            if skill.name == "document_inspection":
                if message.attachments:
                    attachment_skill = skill
                continue
            if not skill.triggers:
                continue
            count, specificity = cls._match_score(skill, text)
            if count:
                matched.append((count, specificity, skill))

        matched.sort(key=lambda item: (-item[0], -item[1], item[2].name))
        selected = [item[2] for item in matched[: cls.MAX_MATCHED_SKILLS]]

        if not selected:
            fallback = skill_registry.get_skill(cls.PRIMARY_BY_ROLE[role])
            if fallback:
                selected.append(fallback)
        if attachment_skill:
            selected.insert(0, attachment_skill)
        return selected


skill_router = SkillRouter()
