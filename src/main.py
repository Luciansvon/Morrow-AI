"""Titik masuk utama aplikasi Morrow v0.2."""

import asyncio

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

    # Pilih Channel Adapter
    if settings.channel_adapter.lower() == "telegram":
        adapter = TelegramMultiBotAdapter()
    else:
        adapter = CLIAdapter()

    orchestrator = SystemOrchestrator(adapter)
    await adapter.start()
    print("✅ Sistem siap menerima pesan.")

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

    await adapter.stop()
    await db.close()
    print("\n👋 Sistem Morrow dihentikan dengan aman.")


if __name__ == "__main__":
    asyncio.run(main())
