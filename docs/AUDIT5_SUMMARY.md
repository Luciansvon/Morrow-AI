# Morrow Audit5 Hardening Summary

Status: VERIFIED
Version: 0.2.2
Date: 2026-08-15

## Audit passes

1. Baseline, reproducibility, structure, and dependency review.
2. Orchestrator, routing, collaboration, task, and runtime correctness.
3. Telegram I/O, attachment/file pipeline, OCR/vision, model policy, and cost attribution.
4. SQLite persistence/concurrency, memory, approval, tool policy, and idempotency.
5. Test evidence integrity, CI behavior, documentation claims, and regression coverage.

## Verification

- Strict Ruff check with no CI autofix.
- Pytest: 83 passed on Python 3.11.
- Pytest: 83 passed on Python 3.12.
- Verified-source packaging succeeded.

## Important hardening outcomes

- Atomic Telegram event dedup and safer reply-role routing across long-message chunks.
- Bounded attachment processing with OOXML, image, parser, OCR/vision, and context limits.
- SQLite transaction serialization and lifecycle-safe async locks.
- Group-scoped durable memory and more conservative memory persistence.
- Fail-closed tool policy, transactional approvals, parameter-bound durable idempotency, and safe unknown-result handling.
- Budget-aware model, routing, vision, memory-judge, and collaboration execution.
- Collective-address semantics distinguish team addressing from object quantifiers such as `hitung semua harga`.
- Incomplete/budget-stopped collaboration no longer becomes a false DONE task.
- CI no longer edits source with Ruff autofix before reporting success.
- Removed the misleading aggregate acceptance test that declared unsupported PRD contracts verified.

## Deliberately unresolved product decisions

These remain product/spec decisions rather than hidden implementation assumptions:

- OQ-002 / OQ-004: exact retry, handoff, and terminal failure semantics.
- OQ-003: repeated-agent participation semantics in bounded discussions.
- OQ-005: authority rule for conflicting instructions from multiple whitelisted users.

External services such as real email, calendar, payment, and social-posting connectors are not fabricated by the core. Their tool/approval infrastructure fails safely until a real connector and credentials are configured.
