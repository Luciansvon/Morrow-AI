"""Pengujian Kontrak Penerimaan AC-005, AC-016, AC-017: Skill Registry, Parsing & Access."""

from src.core.types import RoleID
from src.skills.loader import SkillLoader
from src.skills.registry import skill_registry


def test_ac016_skill_md_parsing():
    """AC-016: SkillLoader mampu mem-parsing SKILL.md dengan YAML frontmatter."""
    sample_skill_md = """---
name: sample_analysis
description: Keahlian analisis data contoh
eligible_roles: [marketing, advisor]
---
## Instruksi Khusus
Jalankan analisis data pasar dengan teliti.
"""
    skill = SkillLoader.load_skill_from_text(sample_skill_md)
    assert skill.name == "sample_analysis"
    assert "marketing" in skill.eligible_roles
    assert "advisor" in skill.eligible_roles
    assert "Jalankan analisis data" in skill.instructions


def test_ac005_and_ac017_skill_lookup_and_shared_access():
    """AC-005 & AC-017: Verifikasi skill role-specific vs shared skill."""
    # Manager berhak atas task_coordination dan shared document_inspection
    mgr_skills = [s.name for s in skill_registry.get_eligible_skills_for_role(RoleID.MANAGER)]
    assert "task_coordination" in mgr_skills
    assert "document_inspection" in mgr_skills
    assert "risk_decision_analysis" not in mgr_skills

    # Marketing berhak atas campaign_strategy dan shared document_inspection
    mkt_skills = [s.name for s in skill_registry.get_eligible_skills_for_role(RoleID.MARKETING)]
    assert "campaign_strategy" in mkt_skills
    assert "document_inspection" in mkt_skills
    assert "task_coordination" not in mkt_skills

    # Advisor berhak atas risk_decision_analysis dan shared document_inspection
    adv_skills = [s.name for s in skill_registry.get_eligible_skills_for_role(RoleID.ADVISOR)]
    assert "risk_decision_analysis" in adv_skills
    assert "document_inspection" in adv_skills
