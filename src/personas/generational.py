"""Backward-compatible persona prompt shim.

The active persona source of truth lives in ``src.persona.profiles``. This module is
kept only so older imports do not resurrect the retired generational persona system.
"""

from src.core.types import RoleID, WorkloadType
from src.persona.profiles import persona_context


def build_persona_prompt(role: RoleID, workload: WorkloadType) -> str:
    """Return the active behavioral persona contract for legacy callers."""
    return persona_context(role, workload)
