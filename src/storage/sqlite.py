"""Manajemen koneksi database SQLite asinkron dengan aiosqlite."""

from pathlib import Path
from typing import Any, Optional

import aiosqlite

from src.core.config import settings


class DatabaseManager:
    _instance: Optional["DatabaseManager"] = None

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or settings.sqlite_db_path
        self._connection: aiosqlite.Connection | None = None

    @classmethod
    def get_instance(cls, db_path: str | None = None) -> "DatabaseManager":
        if cls._instance is None:
            cls._instance = cls(db_path)
        return cls._instance

    async def connect(self) -> aiosqlite.Connection:
        """Membuka koneksi database dengan konfigurasi WAL & foreign keys."""
        if self._connection is None:
            # Pastikan folder database ada
            if self.db_path != ":memory:":
                Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

            conn = await aiosqlite.connect(self.db_path)
            conn.row_factory = aiosqlite.Row

            # Konfigurasi PRAGMA untuk keandalan dan performa tinggi
            await conn.execute("PRAGMA foreign_keys = ON;")
            if self.db_path != ":memory:":
                await conn.execute("PRAGMA journal_mode = WAL;")
                await conn.execute("PRAGMA synchronous = NORMAL;")
                await conn.execute("PRAGMA busy_timeout = 5000;")

            self._connection = conn
        return self._connection

    async def init_schema(self, schema_path: str | None = None) -> None:
        """Inisialisasi seluruh tabel dari file schema.sql."""
        conn = await self.connect()
        if schema_path is None:
            schema_path = str(Path(__file__).parent / "schema.sql")

        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()

        await conn.executescript(schema_sql)
        await conn.commit()

        # Inisialisasi default roles jika belum ada
        roles = [
            ("manager", "Manager", "Koordinasi tim, penentuan prioritas, dan manajemen tugas"),
            ("marketing", "Marketing", "Strategi kampanye, riset pasar, dan konten kreatif"),
            ("advisor", "Advisor", "Analisis keputusan strategis dan evaluasi risiko bisnis"),
        ]
        for role_id, display_name, description in roles:
            await conn.execute(
                """
                INSERT OR IGNORE INTO agents (role_id, display_name, description)
                VALUES (?, ?, ?)
                """,
                (role_id, display_name, description),
            )
        await conn.commit()

    async def execute(self, query: str, params: tuple = ()) -> aiosqlite.Cursor:
        conn = await self.connect()
        cursor = await conn.execute(query, params)
        await conn.commit()
        return cursor

    async def fetch_one(self, query: str, params: tuple = ()) -> dict[str, Any] | None:
        conn = await self.connect()
        async with conn.execute(query, params) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None

    async def fetch_all(self, query: str, params: tuple = ()) -> list[dict[str, Any]]:
        conn = await self.connect()
        async with conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def close(self) -> None:
        if self._connection:
            await self._connection.close()
            self._connection = None


# Helper instance
db = DatabaseManager.get_instance()
