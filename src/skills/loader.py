"""Parser dan pemuat file SKILL.md modular."""

from pydantic import BaseModel


class SkillDefinition(BaseModel):
    name: str
    description: str
    eligible_roles: list[str]  # ['manager', 'marketing', 'advisor'] atau ['*']
    instructions: str
    tools: list[str] = []


class SkillLoader:
    """Pemuat keahlian modular dari berkas teks / markdown."""

    @staticmethod
    def load_skill_from_text(content: str) -> SkillDefinition:
        lines = content.strip().split("\n")
        name = "default_skill"
        desc = ""
        eligible_roles = ["*"]
        instructions = content

        # Parsing YAML frontmatter sederhana jika ada
        if lines and lines[0].strip() == "---":
            yaml_lines = []
            body_lines = []
            in_yaml = True
            for line in lines[1:]:
                if in_yaml and line.strip() == "---":
                    in_yaml = False
                    continue
                if in_yaml:
                    yaml_lines.append(line)
                else:
                    body_lines.append(line)

            instructions = "\n".join(body_lines).strip()
            for yline in yaml_lines:
                if yline.startswith("name:"):
                    name = yline.split("name:", 1)[1].strip()
                elif yline.startswith("description:"):
                    desc = yline.split("description:", 1)[1].strip()
                elif yline.startswith("eligible_roles:"):
                    roles_str = yline.split("eligible_roles:", 1)[1].strip()
                    eligible_roles = [r.strip() for r in roles_str.replace("[", "").replace("]", "").split(",") if r.strip()]

        return SkillDefinition(
            name=name,
            description=desc,
            eligible_roles=eligible_roles,
            instructions=instructions,
        )


skill_loader = SkillLoader()
