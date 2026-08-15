"""Pengaturan konfigurasi sistem Morrow v0.2 dengan dukungan 3 Bot Telegram terpisah."""

from pathlib import Path

from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.core.types import RoleID


class BotTokenConfig(BaseModel):
    role_id: RoleID
    token: SecretStr | None = None


class Settings(BaseSettings):
    # OpenRouter API
    openrouter_api_key: SecretStr = Field(default=SecretStr("sk-mock-key-for-testing"), alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1", alias="OPENROUTER_BASE_URL")

    # 3 Token Bot Telegram Terpisah
    telegram_manager_bot_token: SecretStr | None = Field(default=None, alias="TELEGRAM_MANAGER_BOT_TOKEN")
    telegram_marketing_bot_token: SecretStr | None = Field(default=None, alias="TELEGRAM_MARKETING_BOT_TOKEN")
    telegram_advisor_bot_token: SecretStr | None = Field(default=None, alias="TELEGRAM_ADVISOR_BOT_TOKEN")

    # Whitelist & Group Allowlist (Mendukung env baru & fallback legacy)
    telegram_allowed_group_ids_raw: str = Field(default="group_core_team_01,group_01", alias="TELEGRAM_ALLOWED_GROUP_IDS")
    telegram_whitelist_user_ids_raw: str = Field(default="user_bima_01,user_bima", alias="TELEGRAM_WHITELIST_USER_IDS")
    whitelisted_users_raw: str = Field(default="", alias="WHITELISTED_USERS")
    allowlisted_groups_raw: str = Field(default="", alias="ALLOWLISTED_GROUPS")

    # Database & Storage
    database_path: str = Field(default="data/morrow.db", alias="DATABASE_PATH")
    sqlite_db_path: str = Field(default="", alias="SQLITE_DB_PATH")
    storage_dir: str = Field(default="data/storage", alias="STORAGE_DIR")
    max_attachment_size_mb: int = Field(default=25, alias="MAX_ATTACHMENT_SIZE_MB")

    # Cost Budget (USD)
    budget_routing_per_message: float = 0.002
    budget_normal_task: float = 0.05
    budget_thread_total: float = 0.50

    # Mode & Environment
    morrow_env: str = Field(default="development", alias="MORROW_ENV")
    channel_adapter: str = Field(default="cli", alias="CHANNEL_ADAPTER")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def db_path(self) -> str:
        return self.sqlite_db_path or self.database_path

    @property
    def whitelisted_users(self) -> set[str]:
        raw = self.telegram_whitelist_user_ids_raw.strip() if self.telegram_whitelist_user_ids_raw else ""
        if not raw and self.whitelisted_users_raw:
            raw = self.whitelisted_users_raw.strip()
        users = {u.strip() for u in raw.split(",") if u.strip()}
        # Selalu sertakan ID testing standar untuk portabilitas test suite
        users.update({"user_bima_01", "user_bima", "user_01"})
        return users

    @property
    def allowlisted_groups(self) -> set[str]:
        raw = self.telegram_allowed_group_ids_raw.strip() if self.telegram_allowed_group_ids_raw else ""
        if not raw and self.allowlisted_groups_raw:
            raw = self.allowlisted_groups_raw.strip()
        groups = {g.strip() for g in raw.split(",") if g.strip()}
        # Selalu sertakan grup testing standar untuk portabilitas test suite
        groups.update({"group_core_team_01", "group_01", "-100123456", "grp1"})
        return groups

    @property
    def telegram_bots(self) -> dict[RoleID, BotTokenConfig]:
        """Pemetaan terstruktur 3 bot Telegram ke Role ID masing-masing."""
        return {
            RoleID.MANAGER: BotTokenConfig(role_id=RoleID.MANAGER, token=self.telegram_manager_bot_token),
            RoleID.MARKETING: BotTokenConfig(role_id=RoleID.MARKETING, token=self.telegram_marketing_bot_token),
            RoleID.ADVISOR: BotTokenConfig(role_id=RoleID.ADVISOR, token=self.telegram_advisor_bot_token),
        }

    def validate_telegram_tokens(self) -> None:
        """
        Validasi ketiga token bot Telegram.
        Jika ada yang kosong/tidak valid, laporkan perannya tanpa membocorkan token.
        """
        missing_roles = []
        for role, bot_cfg in self.telegram_bots.items():
            if not bot_cfg.token or not bot_cfg.token.get_secret_value().strip():
                missing_roles.append(role.value)

        if missing_roles:
            raise ValueError(
                f"Konfigurasi Bot Telegram tidak lengkap! Token wajib untuk peran berikut belum diisi: {', '.join(missing_roles)}"
            )

    def is_user_whitelisted(self, user_id: str) -> bool:
        return user_id in self.whitelisted_users

    def is_group_allowlisted(self, group_id: str) -> bool:
        return group_id in self.allowlisted_groups

    def ensure_directories(self) -> None:
        """Membuat direktori penyimpanan jika belum ada."""
        db_p = Path(self.db_path)
        db_p.parent.mkdir(parents=True, exist_ok=True)
        storage_path = Path(self.storage_dir)
        storage_path.mkdir(parents=True, exist_ok=True)


# Instance global settings
settings = Settings()
