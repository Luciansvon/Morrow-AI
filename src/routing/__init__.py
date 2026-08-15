"""Routing and Addressing module for Morrow v0.2."""

from src.routing.addressing import addressing_detector
from src.routing.fast_path import fast_path_router
from src.routing.intent import intent_detector
from src.routing.role_router import role_router

__all__ = [
    "addressing_detector",
    "fast_path_router",
    "intent_detector",
    "role_router",
]
