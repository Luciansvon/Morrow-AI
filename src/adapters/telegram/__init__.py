"""Telegram 3-Bot Adapter Module for Morrow v0.2."""

from src.adapters.telegram.adapter import TelegramMultiBotAdapter
from src.adapters.telegram.bot_registry import bot_registry
from src.adapters.telegram.sender import telegram_sender
from src.adapters.telegram.update_normalizer import TelegramUpdateNormalizer

__all__ = [
    "TelegramMultiBotAdapter",
    "TelegramUpdateNormalizer",
    "bot_registry",
    "telegram_sender",
]
