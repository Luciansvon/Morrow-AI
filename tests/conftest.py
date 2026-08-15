"""Global test fixtures. Test IDs dan mock secrets hanya hidup di test suite."""

import pytest
import pytest_asyncio
from pydantic import SecretStr

from src.adapters.cli import CLIAdapter
from src.core.config import settings
from src.core.orchestrator import SystemOrchestrator
from src.storage.sqlite import db
from src.tools.registry import tool_registry


@pytest_asyncio.fixture(autouse=True)
async def init_test_db(tmp_path):
    old_db = settings.sqlite_db_path
    old_storage = settings.storage_dir
    old_vault = settings.memory_vault_dir
    old_users = settings.telegram_whitelist_user_ids_raw
    old_groups = settings.telegram_allowed_group_ids_raw
    old_openrouter_key = settings.openrouter_api_key
    old_tools = dict(tool_registry._tools)

    settings.sqlite_db_path = str(tmp_path / "test_morrow.db")
    settings.storage_dir = str(tmp_path / "storage")
    settings.memory_vault_dir = str(tmp_path / "memory")
    settings.telegram_whitelist_user_ids_raw = "user_bima_01,user_bima,user_01,u1"
    settings.telegram_allowed_group_ids_raw = "group_core_team_01,group_01,-100123456,grp1,g1"
    settings.openrouter_api_key = SecretStr("sk-mock-key-for-testing")
    settings.ensure_directories()
    tool_registry._tools = {}

    db.db_path = settings.db_path
    if db._connection:
        await db.close()
    await db.init_schema()

    yield db

    await db.close()
    settings.sqlite_db_path = old_db
    settings.storage_dir = old_storage
    settings.memory_vault_dir = old_vault
    settings.telegram_whitelist_user_ids_raw = old_users
    settings.telegram_allowed_group_ids_raw = old_groups
    settings.openrouter_api_key = old_openrouter_key
    tool_registry._tools = old_tools
    db.db_path = settings.db_path


@pytest.fixture
def cli_adapter():
    return CLIAdapter()


@pytest.fixture
def orchestrator(cli_adapter):
    return SystemOrchestrator(cli_adapter)
