-- SQLite schema Morrow v0.2.5

CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, platform_user_id TEXT UNIQUE NOT NULL, display_name TEXT NOT NULL, is_whitelisted INTEGER NOT NULL DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS groups (id TEXT PRIMARY KEY, platform_group_id TEXT UNIQUE NOT NULL, title TEXT NOT NULL, is_allowlisted INTEGER NOT NULL DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS agents (role_id TEXT PRIMARY KEY, display_name TEXT NOT NULL, description TEXT, status TEXT NOT NULL DEFAULT 'active');
CREATE TABLE IF NOT EXISTS messages (id TEXT PRIMARY KEY, platform_message_id TEXT NOT NULL, group_id TEXT NOT NULL, sender_id TEXT NOT NULL, role_id TEXT, content TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS message_agent_map (platform_message_id TEXT PRIMARY KEY, originating_role_id TEXT NOT NULL, bot_identity TEXT, group_id TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS memories (id TEXT PRIMARY KEY, group_id TEXT NOT NULL DEFAULT '__global__', scope TEXT NOT NULL, role_id TEXT, key TEXT NOT NULL, value TEXT NOT NULL, memory_type TEXT NOT NULL DEFAULT 'fact', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE UNIQUE INDEX IF NOT EXISTS idx_memories_shared_unique ON memories(group_id, key) WHERE scope = 'shared';
CREATE UNIQUE INDEX IF NOT EXISTS idx_memories_role_unique ON memories(group_id, role_id, key) WHERE scope = 'role';
CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(memory_id UNINDEXED, group_id UNINDEXED, scope UNINDEXED, role_id UNINDEXED, key, value, memory_type UNINDEXED, tokenize='unicode61 remove_diacritics 2');
CREATE TRIGGER IF NOT EXISTS trg_memories_fts_insert AFTER INSERT ON memories BEGIN INSERT INTO memory_fts(memory_id, group_id, scope, role_id, key, value, memory_type) VALUES (new.id, new.group_id, new.scope, new.role_id, new.key, new.value, new.memory_type); END;
CREATE TRIGGER IF NOT EXISTS trg_memories_fts_update AFTER UPDATE ON memories BEGIN DELETE FROM memory_fts WHERE memory_id = old.id; INSERT INTO memory_fts(memory_id, group_id, scope, role_id, key, value, memory_type) VALUES (new.id, new.group_id, new.scope, new.role_id, new.key, new.value, new.memory_type); END;
CREATE TRIGGER IF NOT EXISTS trg_memories_fts_delete AFTER DELETE ON memories BEGIN DELETE FROM memory_fts WHERE memory_id = old.id; END;
CREATE TABLE IF NOT EXISTS memory_vector_map (vector_id INTEGER PRIMARY KEY AUTOINCREMENT, memory_id TEXT UNIQUE NOT NULL, content_hash TEXT NOT NULL, model TEXT NOT NULL, dimensions INTEGER NOT NULL, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS memory_audit (id TEXT PRIMARY KEY, memory_id TEXT, group_id TEXT NOT NULL DEFAULT '__global__', scope TEXT NOT NULL, role_id TEXT, key TEXT NOT NULL, old_value TEXT, new_value TEXT NOT NULL, changed_by_actor TEXT NOT NULL, changed_by_role TEXT, reason TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, group_id TEXT NOT NULL, title TEXT NOT NULL, description TEXT, current_owner TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'todo', retry_count INTEGER NOT NULL DEFAULT 0, max_retries INTEGER NOT NULL DEFAULT 3, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS task_dependencies (task_id TEXT NOT NULL, depends_on_task_id TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', PRIMARY KEY (task_id, depends_on_task_id), FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE, FOREIGN KEY (depends_on_task_id) REFERENCES tasks(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS task_handoffs (id TEXT PRIMARY KEY, task_id TEXT NOT NULL, from_role TEXT NOT NULL, to_role TEXT NOT NULL, reason TEXT, context_payload TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS attachments (id TEXT PRIMARY KEY, file_id TEXT UNIQUE NOT NULL, original_name TEXT NOT NULL, detected_mime TEXT NOT NULL, file_path TEXT NOT NULL, file_size INTEGER NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS approvals (approval_id TEXT PRIMARY KEY, group_id TEXT NOT NULL, action_type TEXT NOT NULL, normalized_parameters TEXT NOT NULL, parameter_hash TEXT NOT NULL, requested_by_role TEXT NOT NULL, idempotency_key TEXT NOT NULL UNIQUE, status TEXT NOT NULL DEFAULT 'pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, expires_at TIMESTAMP NOT NULL, approved_by TEXT, execution_id TEXT, execution_error TEXT);
CREATE TABLE IF NOT EXISTS threads (thread_id TEXT PRIMARY KEY, group_id TEXT NOT NULL, active_agents TEXT NOT NULL, turn_count INTEGER NOT NULL DEFAULT 0, max_turns INTEGER NOT NULL DEFAULT 4, status TEXT NOT NULL DEFAULT 'active', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS processed_events (event_id TEXT PRIMARY KEY, platform TEXT NOT NULL, group_id TEXT, processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS usage_ledger (id TEXT PRIMARY KEY, request_id TEXT NOT NULL, task_id TEXT, role_id TEXT, group_id TEXT, thread_id TEXT, model TEXT NOT NULL, provider TEXT NOT NULL DEFAULT 'openrouter', input_tokens INTEGER NOT NULL DEFAULT 0, cached_tokens INTEGER NOT NULL DEFAULT 0, reasoning_tokens INTEGER NOT NULL DEFAULT 0, output_tokens INTEGER NOT NULL DEFAULT 0, cost_usd REAL NOT NULL DEFAULT 0.0, latency_ms INTEGER NOT NULL DEFAULT 0, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS tool_executions (
    execution_id TEXT PRIMARY KEY,
    idempotency_key TEXT UNIQUE,
    group_id TEXT,
    thread_id TEXT,
    task_id TEXT,
    role_id TEXT,
    tool_name TEXT NOT NULL,
    parameters_json TEXT NOT NULL,
    classification TEXT NOT NULL DEFAULT 'unknown',
    capability TEXT NOT NULL DEFAULT 'unknown',
    policy_decision TEXT NOT NULL DEFAULT 'unknown',
    approval_id TEXT,
    status TEXT NOT NULL,
    result_json TEXT,
    error_text TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    side_effect INTEGER NOT NULL DEFAULT 0,
    retry_safe INTEGER NOT NULL DEFAULT 0,
    provenance_json TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_tool_executions_context ON tool_executions(group_id, thread_id, task_id, started_at);
CREATE INDEX IF NOT EXISTS idx_tool_executions_tool ON tool_executions(tool_name, started_at);
