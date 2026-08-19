# Morrow Agent Instructions

This file is the repository-level operating contract for coding agents. Read it before modifying code. It exists to prevent locally reasonable changes from violating Morrow product behavior, safety boundaries, or migration plans.

## 1. Product identity

Morrow is a private multi-agent assistant system. Telegram is currently a transport, not the architecture. The system has three durable roles:

- `manager`: operational coordinator, prioritization, delegation, execution ownership.
- `marketing`: growth, campaign, market, content, and marketing analysis.
- `advisor`: strategic analysis, decision support, trade-offs, and risk.

Role behavior/persona may differ, but role authority and safety invariants are core product contracts. Do not merge the three agents into one generic persona or let persona instructions override role authority.

## 2. Source-of-truth hierarchy

Before changing behavior, inspect the relevant files in this order:

1. `AGENTS.md` for repository-wide invariants and current migration boundaries.
2. Latest accepted PRD/spec for the feature being changed.
3. `docs/DECISIONS.md` for accepted product decisions.
4. `docs/ARCHITECTURE.md` for current implementation shape.
5. Latest audit, especially `docs/AUDIT_2026-08-19.md`, for verified gaps.
6. `docs/BUG_BACKLOG.md` and `docs/RELEASE_NOTES.md` only as status documentation. Do not treat a CLOSED label as stronger evidence than source code + reproducible tests.
7. Code and executable tests remain implementation reality.

If documentation and executable behavior disagree, do not silently rewrite product intent to match the code. Preserve the intended contract, fix the implementation, and update stale documentation in the same change when appropriate.

## 3. PRD operating model

Treat PRDs as living, spec-anchored intent contracts. A PRD owns WHY, WHAT, BOUNDARY, DONE, and STOP. Tests/checks verify conformance; code is implementation reality.

Use MUST / SHOULD / MAY for requirements when adding or revising product behavior. Keep in-scope, out-of-scope, non-goals, failure behavior, acceptance criteria, and regression boundaries explicit.

Do not expand scope merely because an adjacent refactor looks attractive.

## 4. Core invariants that MUST survive every change

### Routing and ownership

- Every ordinary user request resolves to one primary owner unless the user explicitly addresses multiple agents or all agents.
- `manager` is coordinator whenever Manager is explicitly included in multi-agent work.
- Collective social messages may produce multiple role replies.
- Collective work may fan out to multiple agents, but durable completion must be tracked per required target.
- Object quantifiers such as `cek semua produk` are not collective addressing.
- Explicit collective forms, including literal `@semua`, natural `semua ...`, `kalian ...`, and equivalent accepted forms, must route consistently.
- Preserve textual role mention order when it matters for contributor order, while keeping Manager coordination authority when Manager is included.

### Control and cancellation

- `stop`, `batal`, `jangan lanjut`, pause, and resume are control intents, not ordinary work prompts.
- Cancellation/pause must invalidate stale in-flight work at a durable ownership/generation boundary, not only change a task label.
- A cancelled or paused run must not later send a stale response or move its task to `done`.
- Do not implement cancellation only with process-local state if durable state is required to survive takeover/restart.

### Task lifecycle

- Dependencies are executable constraints, not metadata decoration.
- A task must not enter runnable/completed states while required dependencies are unfinished.
- Terminal states (`done`, `failed`, `cancelled`) must not reopen through an unconditional status update.
- State transitions must be explicit and testable.
- Persisted `created_at` / `updated_at` values must come from storage when reconstructing models. Do not silently replace DB timestamps with model defaults.
- Multi-agent work must not become `done` unless every required target has succeeded and required synthesis has completed.

### Inbound event ownership

- `processed_events` is a durable ownership/lease protocol, not only a dedup table.
- A takeover must issue a new owner token/generation/attempt identity.
- Completion/failure from an older owner must never mutate the row owned by a newer attempt.
- Duplicate Telegram bot delivery may take over only after the prior owner failed or its lease was abandoned/expired.

### Memory

- Do not store agent speculation, external research claims, or assistant-only facts as durable user memory.
- Explicit user save commands must be durable before acknowledgement.
- Memory must be scoped so data from one user is not accidentally treated as another user's private memory merely because they share a Telegram group.
- Shared group memory and user-private memory are different concepts. Preserve both boundaries when implementing user scope.
- SQLite remains the authoritative local source during the migration described below unless an accepted spec explicitly changes that authority.

### Approvals and external side effects

- External/COMMIT actions require approval. Never bypass the approval gateway because a tool is reachable directly.
- Approval is parameter/state bound and one-shot.
- Unknown external outcomes are not automatically retried.
- Crash recovery must not blindly replay a side effect whose outcome is uncertain.
- An approval stuck in `executing` needs a lease/recovery state machine, not an unconditional reset to `approved`.

### Tool execution

- Tool discovery is capability exposure, not permission.
- Unknown/unclassified tools fail closed.
- Public tool JSON Schema must be enforced at the executor boundary, not merely shown to the LLM.
- Skills must not advertise tools that are not actually registered/callable.
- Browser COMMIT remains approval-gated and state-fingerprint checked.

### Files, release, and secrets

- Never package a developer `.env`, API key, bot token, local credential, or secret into a distributable archive by default.
- `.env.example` may document variable names and safe placeholders only.
- Release staging must fail closed on cleanup errors; stale locked staging content must not be silently archived.

## 5. v0.3 migration boundary: orchestrator, OpenViking, Immich

The v0.3 direction is additive and feature-flagged. It MUST preserve current Morrow behavior when disabled.

### Feature flag rule

- `OFF`: existing Morrow routing/orchestration path remains authoritative and behavior-compatible.
- `ON`: the new orchestration adapter may execute plans, but Morrow Core still owns product semantics and policy.
- Roll out in phases. Do not perform a flag-day rewrite.

### Morrow Core owns

Morrow Core remains authoritative for:

- policy and permissions,
- user/group access control,
- role authority,
- routing semantics,
- task/product behavior,
- approval requirements,
- external-action authority,
- durable safety invariants.

An orchestration framework is an execution engine, not the product brain.

### Microsoft Agent Framework boundary

The selected v0.3 direction uses Microsoft Agent Framework as an execution/orchestration layer only. It MUST NOT become the authority for Morrow permissions, approval policy, role semantics, or product routing rules.

If the framework is unavailable or the feature flag is disabled, the existing orchestrator must continue working.

### Temporal boundary

Temporal is deferred/out of scope for the current v0.3 implementation. Do not add it pre-emptively. Reconsider only when Morrow genuinely needs restart-spanning long-running workflows, durable schedules, or complex retry semantics that cannot be cleanly handled by the current durable task/event model.

### OpenViking boundary

OpenViking is the context / memory / knowledge / skills / experience layer for the v0.3 direction.

- Do not build a second competing vector-memory stack next to it once the OpenViking integration path is enabled.
- Integrate through a narrow adapter/interface so Morrow Core is not coupled to OpenViking internals.
- Treat OpenViking as context retrieval/storage infrastructure, not as approval authority or agent-role authority.
- Preserve a controlled fallback/migration path while the feature flag is disabled or OpenViking is unavailable.
- Never let OpenViking ingest secrets, raw approval credentials, or data outside the caller's authorized scope.

### Immich boundary

Immich is the media asset system for image/video indexing and metadata.

- Immich stores/manages media binaries and media-native metadata.
- Immich is NOT general conversational memory and must not replace Morrow/OpenViking knowledge memory.
- OpenViking may store references/identifiers/derived context that point to Immich assets; media binaries stay in Immich.
- Morrow must preserve user/group authorization when looking up Immich assets.
- Integrate through a narrow adapter/interface and feature flag. Missing Immich capability must fail closed or degrade to the existing local attachment path, depending on the requested operation.

### Planned rollout order

1. Orchestration adapter behind feature flag.
2. OpenViking context integration behind feature flag.
3. Immich media integration behind feature flag.
4. Guardrail hardening around cross-system identity/scope/approval.
5. Observability and migration evidence.

Do not reverse this order merely to make a demo appear more complete.

## 6. Current audit baseline to address

The 2026-08-19 audit identified verified gaps that should be treated as open until code + regressions prove otherwise:

- literal `@semua` not recognized as collective;
- targeted cancel does not invalidate an in-flight generation;
- pause does not invalidate/cancel current runs;
- event lease takeover lacks owner token/generation protection;
- task dependencies are stored but not enforced;
- collective execution is still serial where v0.3 parallel mode expects concurrency;
- memory lacks a user boundary;
- approvals can remain permanently stuck in `executing` after crash;
- terminal tasks can reopen and TaskModel timestamps can be synthetic rather than DB timestamps;
- skills advertise task tools not present in the runtime registry;
- executor does not enforce registered JSON Schema;
- Markdown memory-vault path sanitization can collide across distinct group IDs;
- PowerShell setup fallback for `python` is broken;
- release staging cleanup errors are ignored;
- CI does not gate the relevant acceptance/live validator;
- v0.3 OpenViking/Immich/orchestration integration was not yet present at the audit baseline;
- release/backlog documentation overstates some CLOSED/production-ready claims.

Do not mark these closed based only on implementation intent. Add a regression test or deterministic acceptance check for each fixed behavior.

## 7. Safe change procedure for agents

Before editing:

1. Read the latest audit and the files directly involved.
2. Identify the invariant being changed.
3. Search for all call sites before changing a public method signature or storage schema.
4. Prefer additive migrations over destructive schema rewrites.
5. Preserve compatibility for existing databases and the feature-flag OFF path.

While editing:

1. Keep changes narrowly scoped.
2. Put authorization/ownership validation at the boundary where state is mutated.
3. Never rely only on prompt instructions for security/safety behavior.
4. Add deterministic tests for races/state transitions when changing concurrency or durability.
5. Avoid hidden network calls in core logic. External systems need explicit adapters, configuration, timeouts, provenance, and failure behavior.

Before claiming done:

1. Run Ruff.
2. Run the complete pytest suite.
3. Run compile/syntax checks.
4. Run `git diff --check`.
5. Run relevant acceptance validators when available.
6. Verify feature-flag OFF compatibility.
7. Verify no secret entered the diff or release artifact.
8. Update audit/backlog/release notes only to claims supported by executable evidence.

## 8. Forbidden shortcuts

Do NOT:

- rewrite Morrow around a framework merely because the framework offers its own router/memory/approval primitives;
- bypass Morrow Core policy for Microsoft Agent Framework, OpenViking, Immich, browser, or any connector;
- use Immich as generic chat memory;
- keep two independent semantic-memory authorities active without an explicit migration contract;
- mark work complete because unit tests pass while a known acceptance invariant remains untested;
- silently change external-action approval behavior;
- add Temporal in the current scope;
- delete backward-compatible paths before the feature-flagged replacement has evidence;
- turn every multi-agent request into unrestricted parallel chatter;
- put production credentials in source, tests, fixtures, logs, docs, or release packages.

## 9. When scope is ambiguous

Prefer the smallest change that preserves existing behavior and satisfies the accepted spec. If a proposed change would alter routing authority, approval semantics, memory ownership, external side effects, or data isolation, treat it as a product-contract change rather than a refactor.
