"""Titik masuk utama aplikasi Morrow v0.2."""

import asyncio
import sys

# Proteksi encoding untuk Windows Console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from src.adapters.cli import CLIAdapter
from src.adapters.telegram import TelegramMultiBotAdapter
from src.core.config import settings
from src.core.orchestrator import SystemOrchestrator
from src.storage.sqlite import db


async def main():
    print("=" * 60)
    print("  🚀 Memulai Asisten Tim AI Morrow v0.2")
    print(f"  Mode Adapter: {settings.channel_adapter.upper()}")
    print("=" * 60)

    # Inisialisasi struktur database SQLite
    await db.init_schema()
    settings.ensure_directories()
    print("✅ Database initialized")

    # Pilih Channel Adapter (Otomatis Telegram jika token dikonfigurasi)
    use_telegram = (
        settings.channel_adapter.lower() == "telegram"
        or (settings.telegram_manager_bot_token and settings.telegram_marketing_bot_token)
    )

    if use_telegram:
        adapter = TelegramMultiBotAdapter()
    else:
        adapter = CLIAdapter()

    orchestrator = SystemOrchestrator(adapter)
    await adapter.start()

    if isinstance(adapter, CLIAdapter):
        print("\nKetik 'keluar' atau tekan Ctrl+C untuk berhenti.")
        # Loop interaktif CLI
        while adapter._running:
            try:
                user_input = input("\n[Pengguna]: ")
                if user_input.lower() in ("keluar", "exit", "quit"):
                    break

                from src.core.types import NormalizedMessage
                msg = NormalizedMessage(
                    message_id=f"msg_{asyncio.get_event_loop().time()}",
                    group_id="group_core_team_01",
                    sender_id="user_bima_01",
                    sender_name="Bima",
                    text=user_input,
                )
                await orchestrator.handle_incoming_message(msg)
            except (KeyboardInterrupt, EOFError):
                break
    else:
        # Loop standby untuk telegram multi-bot
        try:
            while adapter._running:
                await asyncio.sleep(1)
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass

    await adapter.stop()
    await db.close()
    print("\n👋 Sistem Morrow dihentikan dengan aman.")


if __name__ == "__main__":
    asyncio.run(main())
