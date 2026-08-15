"""Deterministic workload/risk/collaboration analysis. Tidak membuang token untuk sinyal yang jelas."""

import re

from src.core.types import RiskLevel, RoleID, TaskAnalysis, WorkloadType


class TaskAnalyzer:
    CRITICAL_TERMS = re.compile(r"\b(hukum|legal|kontrak|finansial|keuangan|investasi|transaksi|security|keamanan|privasi|irreversible|tidak bisa dibatalkan|krisis|compliance|regulasi)\b", re.IGNORECASE)
    COMPLEX_TERMS = re.compile(r"\b(multi[- ]?step|kompleks|menyeluruh|end[- ]to[- ]end|seluruh proyek|semua departemen|dependensi|roadmap|arsitektur)\b", re.IGNORECASE)
    PLANNING_TERMS = re.compile(r"\b(rencana|plan|planning|strategi|strategy|launch|peluncuran|roadmap|prioritas|sprint|jadwal)\b", re.IGNORECASE)
    MARKETING_TERMS = re.compile(r"\b(marketing|pemasaran|campaign|kampanye|promo|promosi|iklan|ads|branding|brand|copywriting|konten|content|social media|launch|peluncuran)\b", re.IGNORECASE)
    ADVISOR_TERMS = re.compile(r"\b(risiko|risk|trade[- ]?off|keputusan|decision|hukum|legal|finansial|keuangan|investasi|kontrak|security|keamanan|compliance|regulasi)\b", re.IGNORECASE)

    @classmethod
    def analyze(cls, text: str, primary_role: RoleID, attachment_count: int = 0) -> TaskAnalysis:
        clean = text or ""
        risk = RiskLevel.LOW
        workload = WorkloadType.ROUTINE
        if cls.CRITICAL_TERMS.search(clean):
            risk = RiskLevel.HIGH
            workload = WorkloadType.CRITICAL
        elif cls.COMPLEX_TERMS.search(clean) or attachment_count >= 3:
            risk = RiskLevel.MEDIUM
            workload = WorkloadType.COMPLEX_PLANNING
        elif cls.PLANNING_TERMS.search(clean):
            workload = WorkloadType.PLANNING

        collaborators: list[RoleID] = []
        if primary_role == RoleID.MANAGER:
            if cls.MARKETING_TERMS.search(clean):
                collaborators.append(RoleID.MARKETING)
            if cls.ADVISOR_TERMS.search(clean) and RoleID.ADVISOR not in collaborators:
                collaborators.append(RoleID.ADVISOR)
        elif primary_role == RoleID.MARKETING and cls.ADVISOR_TERMS.search(clean):
            collaborators.append(RoleID.ADVISOR)

        return TaskAnalysis(
            workload=workload,
            risk_level=risk,
            collaborators=collaborators,
            reason="deterministic workload/risk/collaboration signals",
        )


task_analyzer = TaskAnalyzer()
