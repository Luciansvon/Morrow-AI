-- Skema Database SQLite Morrow v0.2
-- 14 Tabel Relasional Durable

-- 1. Pengguna
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    platform_user_id TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    is_whitelisted INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Grup Percakapan
CREATE TABLE IF NOT EXISTS groups (
    id TEXT PRIMARY KEY,
    platform_group_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    is_allowlisted INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Profil & Identitas Agen
CREATE TABLE IF NOT EXISTS agents (
    role_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'active'
);

-- 4. Pesan Percakapan
CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    platform_message_id TEXT NOT NULL,
    group_id TEXT NOT NULL,
    sender_id TEXT NOT NULL,
    role_id TEXT,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Pemetaan Pesan ke Agen (Kunci Reply-Aware Routing Durable)
CREATE TABLE IF NOT EXISTS message_agent_map (
    platform_message_id TEXT PRIMARY KEY,
    originating_role_id TEXT NOT NULL,
    bot_identity TEXT,
    group_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Memori Aktif (Role Memory & Shared Memory)
CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    scope TEXT NOT NULL, -- 'role' atau 'shared'
    role_id TEXT,        -- NULL jika shared
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    memory_type TEXT NOT NULL DEFAULT 'fact',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(scope, role_id, key)
);

-- 7. Riwayat Audit Perubahan Memori
CREATE TABLE IF NOT EXISTS memory_audit (
    id TEXT PRIMARY KEY,
    memory_id TEXT,
    scope TEXT NOT NULL,
    role_id TEXT,
    key TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT NOT NULL,
    changed_by_actor TEXT NOT NULL,
    changed_by_role TEXT,
    reason TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. Siklus Hidup Tugas
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    group_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    current_owner TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'todo', -- 'todo', 'in_progress', 'blocked', 'done', 'cancelled'
    retry_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 9. Dependensi Tugas
CREATE TABLE IF NOT EXISTS task_dependencies (
    task_id TEXT NOT NULL,
    depends_on_task_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    PRIMARY KEY (task_id, depends_on_task_id),
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (depends_on_task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

-- 10. Jejak Delegasi / Handoff
CREATE TABLE IF NOT EXISTS task_handoffs (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    from_role TEXT NOT NULL,
    to_role TEXT NOT NULL,
    reason TEXT,
    context_payload TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

-- 11. Metadata Berkas Lampiran
CREATE TABLE IF NOT EXISTS attachments (
    id TEXT PRIMARY KEY,
    file_id TEXT UNIQUE NOT NULL,
    original_name TEXT NOT NULL,
    detected_mime TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 12. Gerbang Persetujuan Tindakan Luar
CREATE TABLE IF NOT EXISTS approvals (
    approval_id TEXT PRIMARY KEY,
    group_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    normalized_parameters TEXT NOT NULL,
    parameter_hash TEXT NOT NULL,
    requested_by_role TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'approved', 'rejected', 'expired', 'executed'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    approved_by TEXT,
    execution_id TEXT
);

-- 13. Sesi Diskusi Antar Agen (Anti-Loop Tracker)
CREATE TABLE IF NOT EXISTS threads (
    thread_id TEXT PRIMARY KEY,
    group_id TEXT NOT NULL,
    active_agents TEXT NOT NULL, -- JSON list of roles
    turn_count INTEGER NOT NULL DEFAULT 0,
    max_turns INTEGER NOT NULL DEFAULT 4,
    status TEXT NOT NULL DEFAULT 'active', -- 'active', 'resolved', 'waiting_user'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 14. Deduplikasi Event Masuk (AC-021)
CREATE TABLE IF NOT EXISTS processed_events (
    event_id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 15. Buku Besar Biaya & Penggunaan Token (Usage Ledger)
CREATE TABLE IF NOT EXISTS usage_ledger (
    id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL,
    task_id TEXT,
    role_id TEXT,
    model TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT 'openrouter',
    input_tokens INTEGER NOT NULL DEFAULT 0,
    cached_tokens INTEGER NOT NULL DEFAULT 0,
    reasoning_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd REAL NOT NULL DEFAULT 0.0,
    latency_ms INTEGER NOT NULL DEFAULT 0,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
