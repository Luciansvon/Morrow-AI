"""Konfigurasi Morrow. Rahasia selalu dibungkus SecretStr dan tidak dicetak mentah."""

from pathlib import Path

from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.core.types import RoleID


class BotTokenConfig(BaseModel):
    role_id: RoleID
    token: SecretStr | None = None


class Settings(BaseSettings):
    openrouter_api_key: SecretStr = Field(default=SecretStr(""), alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1", alias="OPENROUTER_BASE_URL")

    telegram_manager_bot_token: SecretStr | None = Field(default=None, alias="TELEGRAM_MANAGER_BOT_TOKEN")
    telegram_marketing_bot_token: SecretStr | None = Field(default=None, alias="TELEGRAM_MARKETING_BOT_TOKEN")
    telegram_advisor_bot_token: SecretStr | None = Field(default=None, alias="TELEGRAM_ADVISOR_BOT_TOKEN")
    telegram_drop_pending_updates: bool = Field(default=False, alias="TELEGRAM_DROP_PENDING_UPDATES")

    telegram_allowed_group_ids_raw: str = Field(default="", alias="TELEGRAM_ALLOWED_GROUP_IDS")
    telegram_whitelist_user_ids_raw: str = Field(default="", alias="TELEGRAM_WHITELIST_USER_IDS")
    whitelisted_users_raw: str = Field(default="", alias="WHITELISTED_USERS")
    allowlisted_groups_raw: str = Field(default="", alias="ALLOWLISTED_GROUPS")

    database_path: str = Field(default="data/morrow.db", alias="DATABASE_PATH")
    sqlite_db_path: str = Field(default="", alias="SQLITE_DB_PATH")
    storage_dir: str = Field(default="data/storage", alias="STORAGE_DIR")
    memory_vault_dir: str = Field(default="data/memory", alias="MEMORY_VAULT_DIR")
    memory_embedding_model: str = Field(
        default="openai/text-embedding-3-small",
        alias="MEMORY_EMBEDDING_MODEL",
    )
    memory_embedding_dimensions: int = Field(
        default=384,
        gt=0,
        le=4096,
        alias="MEMORY_EMBEDDING_DIMENSIONS",
    )
    memory_embedding_max_chars: int = Field(
        default=4000,
        gt=0,
        alias="MEMORY_EMBEDDING_MAX_CHARS",
    )
    memory_hybrid_top_k: int = Field(default=8, gt=0, le=50, alias="MEMORY_HYBRID_TOP_K")
    memory_semantic_enabled: bool = Field(default=True, alias="MEMORY_SEMANTIC_ENABLED")
    memory_semantic_backfill_limit: int = Field(
        default=200,
        ge=0,
        le=5000,
        alias="MEMORY_SEMANTIC_BACKFILL_LIMIT",
    )
    max_attachment_size_mb: int = Field(default=20, gt=0, alias="MAX_ATTACHMENT_SIZE_MB")
    max_attachment_context_chars: int = Field(default=12_000, gt=0, alias="MAX_ATTACHMENT_CONTEXT_CHARS")
    max_total_attachment_context_chars: int = Field(default=24_000, gt=0, alias="MAX_TOTAL_ATTACHMENT_CONTEXT_CHARS")
    max_pdf_ocr_pages: int = Field(default=5, gt=0, alias="MAX_PDF_OCR_PAGES")
    max_archive_entries: int = Field(default=5000, gt=0, alias="MAX_ARCHIVE_ENTRIES")
    max_archive_uncompressed_mb: int = Field(default=100, gt=0, alias="MAX_ARCHIVE_UNCOMPRESSED_MB")
    max_spreadsheet_rows: int = Field(default=20000, gt=0, alias="MAX_SPREADSHEET_ROWS")
    max_spreadsheet_cells: int = Field(default=250000, gt=0, alias="MAX_SPREADSHEET_CELLS")
    max_image_pixels: int = Field(default=40000000, gt=0, alias="MAX_IMAGE_PIXELS")
    max_document_extract_chars: int = Field(default=200000, gt=0, alias="MAX_DOCUMENT_EXTRACT_CHARS")
    max_message_context_chars: int = Field(default=20_000, gt=0, alias="MAX_MESSAGE_CONTEXT_CHARS")
    max_memory_context_chars: int = Field(default=12_000, gt=0, alias="MAX_MEMORY_CONTEXT_CHARS")
    max_active_tasks_context: int = Field(default=50, gt=0, alias="MAX_ACTIVE_TASKS_CONTEXT")
    max_agent_output_tokens: int = Field(default=4000, gt=0, alias="MAX_AGENT_OUTPUT_TOKENS")
    max_router_output_tokens: int = Field(default=256, gt=0, alias="MAX_ROUTER_OUTPUT_TOKENS")
    max_memory_judge_output_tokens: int = Field(default=768, gt=0, alias="MAX_MEMORY_JUDGE_OUTPUT_TOKENS")
    max_vision_output_tokens: int = Field(default=1200, gt=0, alias="MAX_VISION_OUTPUT_TOKENS")
    openrouter_timeout_seconds: float = Field(default=180.0, gt=0, alias="OPENROUTER_TIMEOUT_SECONDS")

    budget_routing_per_message: float = Field(default=0.002, ge=0, alias="BUDGET_ROUTING_PER_MESSAGE")
    budget_normal_task: float = Field(default=0.05, ge=0, alias="BUDGET_NORMAL_TASK")
    budget_thread_total: float = Field(default=0.50, gt=0, alias="BUDGET_THREAD_TOTAL")

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
        return {u.strip() for u in raw.split(",") if u.strip()}

    @property
    def allowlisted_groups(self) -> set[str]:
        raw = self.telegram_allowed_group_ids_raw.strip() if self.telegram_allowed_group_ids_raw else ""
        if not raw and self.allowlisted_groups_raw:
            raw = self.allowlisted_groups_raw.strip()
        return {g.strip() for g in raw.split(",") if g.strip()}

    @property
    def telegram_bots(self) -> dict[RoleID, BotTokenConfig]:
        return {
            RoleID.MANAGER: BotTokenConfig(role_id=RoleID.MANAGER, token=self.telegram_manager_bot_token),
            RoleID.MARKETING: BotTokenConfig(role_id=RoleID.MARKETING, token=self.telegram_marketing_bot_token),
            RoleID.ADVISOR: BotTokenConfig(role_id=RoleID.ADVISOR, token=self.telegram_advisor_bot_token),
        }

    @property
    def configured_telegram_token_count(self) -> int:
        return sum(
            1
            for cfg in self.telegram_bots.values()
            if cfg.token and cfg.token.get_secret_value().strip()
        )

    def validate_openrouter_key(self, *, allow_mock: bool = False) -> None:
        value = self.openrouter_api_key.get_secret_value().strip()
        if not value:
            raise ValueError("OPENROUTER_API_KEY wajib diisi sebelum Morrow dijalankan.")
        if value.startswith("sk-mock") and not allow_mock:
            raise ValueError("OPENROUTER_API_KEY masih menggunakan mock/testing key.")

    def validate_telegram_tokens(self) -> None:
        missing_roles = []
        for role, bot_cfg in self.telegram_bots.items():
            if not bot_cfg.token or not bot_cfg.token.get_secret_value().strip():
                missing_roles.append(role.value)
        if missing_roles:
            raise ValueError(
                "Konfigurasi Bot Telegram tidak lengkap. Token wajib belum diisi untuk: "
                + ", ".join(missing_roles)
            )

    def validate_telegram_access(self) -> None:
        if not self.allowlisted_groups:
            raise ValueError("TELEGRAM_ALLOWED_GROUP_IDS wajib diisi saat adapter Telegram aktif.")
        if not self.whitelisted_users:
            raise ValueError("TELEGRAM_WHITELIST_USER_IDS wajib diisi saat adapter Telegram aktif.")

    def is_user_whitelisted(self, user_id: str) -> bool:
        return str(user_id) in self.whitelisted_users

    def is_group_allowlisted(self, group_id: str) -> bool:
        return str(group_id) in self.allowlisted_groups

    def ensure_directories(self) -> None:
        db_p = Path(self.db_path)
        if self.db_path != ":memory:":
            db_p.parent.mkdir(parents=True, exist_ok=True)
        Path(self.storage_dir).mkdir(parents=True, exist_ok=True)
        Path(self.memory_vault_dir).mkdir(parents=True, exist_ok=True)


settings = Settings()
