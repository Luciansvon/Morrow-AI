"""SQLite async manager dengan WAL, FTS5, sqlite-vec, migrasi, dan integrity check."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

import aiosqlite

from src.core.config import settings


class DatabaseManager:
    _instance: Optional["DatabaseManager"] = None

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or settings.db_path
        self._connection: aiosqlite.Connection | None = None
        self._connect_lock = asyncio.Lock()
        self._transaction_lock = asyncio.Lock()
        self._vector_extension_loaded = False

    @classmethod
    def get_instance(cls, db_path: str | None = None) -> "DatabaseManager":
        if cls._instance is None:
            cls._instance = cls(db_path)
        return cls._instance

    @property
    def vector_extension_loaded(self) -> bool:
        return self._vector_extension_loaded

    async def _try_load_vector_extension(self, conn: aiosqlite.Connection) -> None:
        self._vector_extension_loaded = False
        if not settings.memory_semantic_enabled:
            return
        try:
            import sqlite_vec

            await conn.enable_load_extension(True)
            await conn.load_extension(sqlite_vec.loadable_path())
            async with conn.execute("SELECT vec_version()") as cursor:
                row = await cursor.fetchone()
            self._vector_extension_loaded = bool(row)
        except Exception:
            self._vector_extension_loaded = False
        finally:
            try:
                await conn.enable_load_extension(False)
            except Exception:
                pass

    async def connect(self) -> aiosqlite.Connection:
        if self._connection is not None:
            return self._connection
        async with self._connect_lock:
            if self._connection is None:
                if self.db_path != ":memory:":
                    Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
                conn = await aiosqlite.connect(self.db_path)
                conn.row_factory = aiosqlite.Row
                await conn.execute("PRAGMA foreign_keys = ON;")
                if self.db_path != ":memory:":
                    await conn.execute("PRAGMA journal_mode = WAL;")
                    await conn.execute("PRAGMA synchronous = NORMAL;")
                    await conn.execute("PRAGMA busy_timeout = 5000;")
                await self._try_load_vector_extension(conn)
                self._connection = conn
        assert self._connection is not None
        return self._connection

    async def _table_columns(self, table: str) -> set[str]:
        conn = await self.connect()
        async with conn.execute(f"PRAGMA table_info({table})") as cursor:
            rows = await cursor.fetchall()
        return {row["name"] for row in rows}

    async def _table_exists(self, table: str) -> bool:
        row = await self.fetch_one(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        )
        return bool(row)

    async def _migrate_legacy_schema(self) -> None:
        conn = await self.connect()
        if await self._table_exists("memories"):
            cols = await self._table_columns("memories")
            if "group_id" not in cols:
                await conn.execute("ALTER TABLE memories RENAME TO memories_legacy_v02")
                await conn.execute(
                    """CREATE TABLE memories (
                        id TEXT PRIMARY KEY,
                        group_id TEXT NOT NULL DEFAULT '__global__',
                        scope TEXT NOT NULL,
                        role_id TEXT,
                        key TEXT NOT NULL,
                        value TEXT NOT NULL,
                        memory_type TEXT NOT NULL DEFAULT 'fact',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )"""
                )
                await conn.execute(
                    """INSERT INTO memories
                       (id, group_id, scope, role_id, key, value, memory_type, created_at, updated_at)
                       SELECT id, '__global__', scope, role_id, key, value, memory_type, created_at, updated_at
                       FROM memories_legacy_v02"""
                )
                await conn.execute("DROP TABLE memories_legacy_v02")

        migrations = {
            "memory_audit": [("group_id", "TEXT NOT NULL DEFAULT '__global__'")],
            "tasks": [("max_retries", "INTEGER NOT NULL DEFAULT 3")],
            "approvals": [("execution_error", "TEXT")],
            "processed_events": [("group_id", "TEXT")],
            "usage_ledger": [("group_id", "TEXT"), ("thread_id", "TEXT")],
        }
        for table, additions in migrations.items():
            if not await self._table_exists(table):
                continue
            cols = await self._table_columns(table)
            for col, ddl in additions:
                if col not in cols:
                    await conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")

        if await self._table_exists("memories"):
            await conn.execute(
                """DELETE FROM memories WHERE id IN (
                    SELECT id FROM (
                        SELECT id,
                               ROW_NUMBER() OVER (
                                   PARTITION BY group_id, scope,
                                     CASE WHEN scope='role' THEN COALESCE(role_id, '') ELSE '' END,
                                     key
                                   ORDER BY updated_at DESC, created_at DESC, rowid DESC
                               ) AS rn
                        FROM memories
                    ) ranked WHERE rn > 1
                )"""
            )
        await conn.commit()

    async def _ensure_memory_vector_schema(self, conn: aiosqlite.Connection) -> None:
        if not self._vector_extension_loaded or not settings.memory_semantic_enabled:
            return
        dimensions = settings.memory_embedding_dimensions
        async with conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='memory_vec'"
        ) as cursor:
            row = await cursor.fetchone()
        if row and f"float[{dimensions}]" not in str(row["sql"] or "").lower():
            await conn.execute("DROP TABLE memory_vec")
            await conn.execute("DELETE FROM memory_vector_map")
        await conn.execute(
            f"""CREATE VIRTUAL TABLE IF NOT EXISTS memory_vec USING vec0(
                vector_id INTEGER PRIMARY KEY,
                embedding FLOAT[{dimensions}] distance_metric=cosine,
                group_id TEXT PARTITION KEY,
                scope TEXT,
                role_id TEXT
            )"""
        )

    async def init_schema(self, schema_path: str | None = None) -> None:
        conn = await self.connect()
        await self._migrate_legacy_schema()
        if schema_path is None:
            schema_path = str(Path(__file__).parent / "schema.sql")
        with open(schema_path, "r", encoding="utf-8") as f:
            await conn.executescript(f.read())

        await conn.execute("DELETE FROM memory_fts")
        await conn.execute(
            """INSERT INTO memory_fts
               (memory_id, group_id, scope, role_id, key, value, memory_type)
               SELECT id, group_id, scope, role_id, key, value, memory_type FROM memories"""
        )
        await self._ensure_memory_vector_schema(conn)

        roles = [
            ("manager", "Manager", "Koordinasi tim, prioritas, dan manajemen tugas"),
            ("marketing", "Marketing", "Strategi kampanye, riset pasar, dan konten kreatif"),
            ("advisor", "Advisor", "Analisis keputusan strategis dan risiko"),
        ]
        await conn.executemany(
            "INSERT OR IGNORE INTO agents (role_id, display_name, description) VALUES (?, ?, ?)",
            roles,
        )
        await conn.commit()

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[aiosqlite.Connection]:
        async with self._transaction_lock:
            conn = await self.connect()
            await conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
                await conn.commit()
            except Exception:
                await conn.rollback()
                raise

    async def execute(self, query: str, params: tuple = ()) -> aiosqlite.Cursor:
        async with self._transaction_lock:
            conn = await self.connect()
            cursor = await conn.execute(query, params)
            await conn.commit()
            return cursor

    async def fetch_one(self, query: str, params: tuple = ()) -> dict[str, Any] | None:
        async with self._transaction_lock:
            conn = await self.connect()
            async with conn.execute(query, params) as cursor:
                row = await cursor.fetchone()
            return dict(row) if row else None

    async def fetch_all(self, query: str, params: tuple = ()) -> list[dict[str, Any]]:
        async with self._transaction_lock:
            conn = await self.connect()
            async with conn.execute(query, params) as cursor:
                rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def integrity_check(self) -> bool:
        row = await self.fetch_one("PRAGMA quick_check")
        return bool(row) and next(iter(row.values())) == "ok"

    async def close(self) -> None:
        if self._connection:
            await self._connection.close()
            self._connection = None
        self._vector_extension_loaded = False
        self._connect_lock = asyncio.Lock()
        self._transaction_lock = asyncio.Lock()


db = DatabaseManager.get_instance()
