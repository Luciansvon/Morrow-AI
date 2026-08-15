"""Morrow entrypoint."""

import asyncio
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from src import __version__
from src.adapters.cli import CLIAdapter
from src.adapters.telegram import TelegramMultiBotAdapter
from src.core.config import settings
from src.core.orchestrator import SystemOrchestrator
from src.core.types import NormalizedMessage
from src.storage.sqlite import db


async def main() -> None:
    print("=" * 60)
    print(f"  🚀 Morrow v{__version__}")
    print("=" * 60)

    settings.validate_openrouter_key()
    settings.ensure_directories()

    # Config may be loaded before tests/runtime mutate SQLITE_DB_PATH.
    if db._connection is None and db.db_path != settings.db_path:
        db.db_path = settings.db_path
    await db.init_schema()
    if not await db.integrity_check():
        raise RuntimeError("SQLite quick_check gagal")
    print(f"✅ Database initialized: {settings.db_path}")

    token_count = settings.configured_telegram_token_count
    explicit_telegram = settings.channel_adapter.lower() == "telegram"
    if explicit_telegram or token_count:
        if token_count != 3:
            raise ValueError("Mode Telegram membutuhkan tepat 3 token bot: Manager, Marketing, Advisor.")
        adapter = TelegramMultiBotAdapter()
    else:
        adapter = CLIAdapter()

    orchestrator = SystemOrchestrator(adapter)
    try:
        await adapter.start()
        if isinstance(adapter, CLIAdapter):
            while adapter._running:
                try:
                    user_input = input("\n[Pengguna]: ")
                except (KeyboardInterrupt, EOFError):
                    break
                if user_input.lower() in {"keluar", "exit", "quit"}:
                    break
                await orchestrator.handle_incoming_message(
                    NormalizedMessage(
                        message_id=f"msg_{asyncio.get_running_loop().time()}",
                        group_id="__cli__",
                        sender_id="__cli_user__",
                        sender_name="User",
                        text=user_input,
                        platform="cli",
                    )
                )
        else:
            while adapter._running:
                adapter.raise_if_unhealthy()
                await asyncio.sleep(1)
    finally:
        await adapter.stop()
        await db.close()
        print("\nMorrow dihentikan dengan aman.")


if __name__ == "__main__":
    asyncio.run(main())
