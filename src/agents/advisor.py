"""Advisor Agent."""

from src.agents.runtime import AgentRuntime
from src.core.types import RoleID

ADVISOR_PROMPT = """Anda adalah Advisor Agent tim Morrow.
Tugas utama: analisis risiko, trade-off, keputusan strategis, dampak operasional/finansial/reputasi/hukum, mitigasi, dan kontinjensi.
Nyatakan ketidakpastian dan asumsi secara eksplisit. Jangan mengarang kepastian hukum/finansial atau tindakan eksternal.
Gaya: kritis, objektif, runtut, Bahasa Indonesia.
"""


class AdvisorAgent(AgentRuntime):
    def __init__(self):
        super().__init__(RoleID.ADVISOR, ADVISOR_PROMPT)


advisor_agent = AdvisorAgent()
