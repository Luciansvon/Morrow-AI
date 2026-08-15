"""Parser SKILL.md ringan dengan frontmatter aman dan default immutable."""

from pydantic import BaseModel, Field


class SkillDefinition(BaseModel):
    name: str
    description: str = ""
    eligible_roles: list[str] = Field(default_factory=lambda: ["*"])
    instructions: str = ""
    tools: list[str] = Field(default_factory=list)
    triggers: list[str] = Field(default_factory=list)


class SkillLoader:
    @staticmethod
    def _parse_list(value: str) -> list[str]:
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            value = value[1:-1]
        return [item.strip().strip("'\"") for item in value.split(",") if item.strip()]

    @staticmethod
    def load_skill_from_text(content: str) -> SkillDefinition:
        lines = content.strip().splitlines()
        meta: dict[str, str] = {}
        body = content.strip()
        if lines and lines[0].strip() == "---":
            end = next((i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---"), None)
            if end is not None:
                for line in lines[1:end]:
                    if ":" in line:
                        key, value = line.split(":", 1)
                        meta[key.strip()] = value.strip()
                body = "\n".join(lines[end + 1 :]).strip()
        return SkillDefinition(
            name=meta.get("name", "default_skill"),
            description=meta.get("description", ""),
            eligible_roles=SkillLoader._parse_list(meta.get("eligible_roles", "*")) or ["*"],
            tools=SkillLoader._parse_list(meta.get("tools", "")),
            triggers=SkillLoader._parse_list(meta.get("triggers", "")),
            instructions=body,
        )


skill_loader = SkillLoader()
