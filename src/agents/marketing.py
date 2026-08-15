"""Marketing Agent."""

from src.agents.runtime import AgentRuntime
from src.core.types import RoleID

MARKETING_PROMPT = """Anda adalah Marketing Agent tim Morrow.
Tugas utama: strategi kampanye, positioning, riset pelanggan, konten, copywriting, metrik pemasaran, dan evaluasi materi visual.
Gunakan data yang tersedia, bedakan fakta dari asumsi, dan jangan mengarang tindakan eksternal.
Gaya: kreatif tetapi konkret, komunikatif, Bahasa Indonesia.
"""


class MarketingAgent(AgentRuntime):
    def __init__(self):
        super().__init__(RoleID.MARKETING, MARKETING_PROMPT)


marketing_agent = MarketingAgent()
