"""Feature-flagged external integrations for Morrow v0.3.

Morrow Core remains authoritative for routing, permissions, approvals, and product behavior.
Integration modules expose narrow infrastructure adapters only.
"""

from src.integrations.immich import ImmichClient, MediaAssetReference
from src.integrations.openviking import OpenVikingClient

__all__ = ["ImmichClient", "MediaAssetReference", "OpenVikingClient"]
