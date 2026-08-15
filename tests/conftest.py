"""Fixtures global untuk pengujian unit & integrasi Morrow v0.2."""

import pytest
import pytest_asyncio

from src.adapters.cli import CLIAdapter
from src.core.config import settings
from src.core.orchestrator import SystemOrchestrator
from src.storage.sqlite import db


@pytest_asyncio.fixture(autouse=True)
async def init_test_db(tmp_path):
    """Menyiapkan database SQLite terisolasi untuk setiap pengujian."""
    test_db_path = str(tmp_path / "test_morrow.db")
    settings.sqlite_db_path = test_db_path
    settings.storage_dir = str(tmp_path / "storage")
    settings.ensure_directories()

    # Buat instance database baru untuk test
    db.db_path = test_db_path
    db._connection = None
    await db.init_schema()

    yield db

    await db.close()
    db._connection = None


@pytest.fixture
def cli_adapter():
    return CLIAdapter()


@pytest.fixture
def orchestrator(cli_adapter):
    return SystemOrchestrator(cli_adapter)
