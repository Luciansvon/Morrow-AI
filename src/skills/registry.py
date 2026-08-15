"""Katalog dan registri keahlian (Skill Registry) untuk Morrow v0.2."""


from src.core.types import RoleID
from src.skills.loader import SkillDefinition


class SkillRegistry:
    """Pusat pendaftaran dan pengecekan kelayakan keahlian agen."""

    def __init__(self):
        self._skills: dict[str, SkillDefinition] = {}
        self._init_default_skills()

    def _init_default_skills(self):
        # 1. Skill Khusus Manager
        self.register_skill(
            SkillDefinition(
                name="task_coordination",
                description="Keahlian manajemen tugas, dependensi, dan delegasi",
                eligible_roles=["manager"],
                instructions="Kelola siklus tugas secara terstruktur. Tentukan prioritas dan delegasikan ke Marketing atau Advisor jika diperlukan.",
                tools=["create_task", "delegate_task", "update_task_status"],
            )
        )
        # 2. Skill Khusus Marketing
        self.register_skill(
            SkillDefinition(
                name="campaign_strategy",
                description="Keahlian riset pasar, positioning, dan pembuatan konten promosi",
                eligible_roles=["marketing"],
                instructions="Rancang strategi kampanye promosi, positioning merek, dan evaluasi materi visual poster atau copywriting.",
                tools=["analyze_campaign", "create_content_brief"],
            )
        )
        # 3. Skill Khusus Advisor
        self.register_skill(
            SkillDefinition(
                name="risk_decision_analysis",
                description="Keahlian evaluasi risiko, analisis trade-off, dan rekomendasi dampak",
                eligible_roles=["advisor"],
                instructions="Analisis untung-rugi dan risiko jangka pendek maupun jangka panjang sebelum keputusan diambil.",
                tools=["evaluate_risk", "propose_decision"],
            )
        )
        # 4. Shared Skill (Dapat diakses semua peran)
        self.register_skill(
            SkillDefinition(
                name="document_inspection",
                description="Keahlian membaca dan mengekstrak informasi dokumen terlampir",
                eligible_roles=["manager", "marketing", "advisor", "*"],
                instructions="Periksa isi dokumen teks/spreadsheet dan gunakan fakta penting untuk menjawab instruksi.",
                tools=["read_attachment"],
            )
        )

    def register_skill(self, skill: SkillDefinition) -> None:
        self._skills[skill.name] = skill

    def get_skill(self, name: str) -> SkillDefinition | None:
        return self._skills.get(name)

    def get_eligible_skills_for_role(self, role: RoleID) -> list[SkillDefinition]:
        """Mengembalikan seluruh skill yang berhak digunakan oleh peran agen tertentu."""
        eligible = []
        for skill in self._skills.values():
            if "*" in skill.eligible_roles or role.value in skill.eligible_roles:
                eligible.append(skill)
        return eligible


skill_registry = SkillRegistry()
