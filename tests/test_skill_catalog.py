"""Regression tests untuk katalog skill modular dan routing bounded."""

from pathlib import Path

from src.core.types import AttachmentInfo, NormalizedMessage, RoleID
from src.skills.loader import SkillLoader
from src.skills.registry import SkillRegistry, skill_registry
from src.skills.router import skill_router


def _message(text: str, attachments: list[AttachmentInfo] | None = None) -> NormalizedMessage:
    return NormalizedMessage(
        message_id="skill_catalog_test",
        group_id="group_skill_test",
        sender_id="user_skill_test",
        text=text,
        platform="cli",
        attachments=attachments or [],
    )


def test_catalog_loads_modular_skill_files():
    registry = SkillRegistry()
    market_research = registry.get_skill("market_research")
    assert market_research is not None
    assert market_research.source_path is not None
    assert market_research.source_path.endswith("SKILL.md")
    assert len(registry.list_skills()) >= 16


def test_catalog_keeps_role_boundaries_and_shared_skills():
    manager = {s.name for s in skill_registry.get_eligible_skills_for_role(RoleID.MANAGER)}
    marketing = {s.name for s in skill_registry.get_eligible_skills_for_role(RoleID.MARKETING)}
    advisor = {s.name for s in skill_registry.get_eligible_skills_for_role(RoleID.ADVISOR)}

    assert {"task_coordination", "prioritization_triage", "dependency_recovery", "progress_review"} <= manager
    assert "market_research" not in manager
    assert {"campaign_strategy", "audience_positioning", "market_research", "content_strategy", "marketing_measurement"} <= marketing
    assert "risk_premortem" not in marketing
    assert {"risk_decision_analysis", "risk_premortem", "scenario_planning", "recommendation_synthesis"} <= advisor
    assert {"document_inspection", "evidence_synthesis", "assumption_audit"} <= manager & marketing & advisor


def test_router_selects_manager_prioritization_skill_only_from_manager_domain():
    names = {s.name for s in skill_router.resolve_skills_for_task(
        RoleID.MANAGER,
        _message("Prioritaskan backlog yang urgent dan tentukan urutan kerja"),
    )}
    assert "prioritization_triage" in names
    assert "market_research" not in names
    assert "risk_decision_analysis" not in names


def test_router_uses_top_three_text_skills_for_multi_signal_marketing_request():
    names = [s.name for s in skill_router.resolve_skills_for_task(
        RoleID.MARKETING,
        _message("Riset pasar kompetitor, positioning target market, lalu campaign launch"),
    )]
    assert len(names) == 3
    assert {"market_research", "audience_positioning", "campaign_strategy"} == set(names)


def test_attachment_skill_is_added_without_losing_role_fallback():
    attachment = AttachmentInfo(
        file_id="file_1",
        original_name="brief.pdf",
        detected_mime="application/pdf",
        file_path="/tmp/brief.pdf",
        file_size=1,
    )
    names = [s.name for s in skill_router.resolve_skills_for_task(
        RoleID.ADVISOR,
        _message("Tolong cek ini", [attachment]),
    )]
    assert names == ["document_inspection", "risk_decision_analysis"]


def test_skill_loader_supports_references_metadata(tmp_path: Path):
    skill_path = tmp_path / "SKILL.md"
    skill_path.write_text(
        "---\nname: sample\neligible_roles: [advisor]\nreferences: [references/checklist.md]\n---\nGunakan checklist.\n",
        encoding="utf-8",
    )
    skill = SkillLoader.load_skill_file(skill_path)
    assert skill.references == ["references/checklist.md"]
    assert skill.source_path == str(skill_path)
