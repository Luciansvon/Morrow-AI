# Morrow v0.2.5 — Reliable Action Layer

Morrow v0.2.5 hardens the tool runtime before broader external integrations are added.

## Scope

This release intentionally focuses on the action layer. Gmail, Google Calendar, richer messaging adapters, persona distillation, cultural datasets, relationship evolution, and general file mutation remain outside this release.

## Progressive tool discovery

Local tools now carry compact metadata: domain, READ/PREPARE/COMMIT capability, risk, side effect, auth requirement, output trust, cost class, retry safety, and discovery keywords. The model is no longer given every local JSON Schema by default. Morrow exposes a small deterministic match set and `morrow_tool_search`; discovered schemas become available on the next tool round.

A tool that was not exposed/discovered for the current run cannot be executed merely because the model guessed its name.

## Execution journal

`tool_executions` is now an action journal rather than only an idempotency cache. It records execution id, optional idempotency key, group/thread/task/role, normalized parameters, policy decision, approval link, result/error, side-effect/retry flags, provenance, and timestamps. The v0.2.4 table is migrated in place and old rows are retained with `policy_decision=legacy_import`.

Unknown tools and approval-gated proposals are journaled even when they do not execute.

## Provenance

Local tool observations include a provenance envelope. Internal deterministic tools are `trusted_internal`; browser/external observations are `external` and taint returned fields by default. This is the first provenance layer, not a complete cross-provider information-flow engine.

## Approval-aware agent loop

When the model requests a classified external tool, Morrow creates a parameter-bound approval, journals the proposal, returns the approval id to the model, and does not execute the side effect. `/approve <id>` executes the exact stored parameters through the existing one-shot gateway and links the resulting tool execution back to the approval.

Repeated identical external calls inside one agent run reuse the same pending approval. Legacy external registrations are still forced to COMMIT, side-effect=true, retry-safe=false by policy.

## Browser backend

`src/browser/base.py` remains provider-neutral. The preferred provider is now `EgoLiteBackend`, which uses Ego Lite's official `ego-browser nodejs` bridge and maps each Morrow task/thread to an isolated Ego Lite Space. `_task_space` is injected by Morrow and is never model-controlled. The older `AgentBrowserBackend` remains a compatibility fallback rather than the primary implementation.

Initial tools:

| Tool | Class | Approval |
|---|---|---|
| `browser_open` | READ | no |
| `browser_snapshot` | READ | no |
| `browser_screenshot` | READ | no |
| `browser_fill` | PREPARE | no |
| `browser_type` | PREPARE | no |
| `browser_click` | COMMIT | required |

`click` remains deliberately conservative because a click can submit, purchase, send, delete, or trigger another external mutation. Provider capability never bypasses Morrow's policy or approval gateway.

The Ego Lite adapter uses official helpers such as `useOrCreateTaskSpace`, `openOrReuseTab`, `snapshotText`, `captureScreenshot`, `fillInput`, and `click` through the `ego-browser nodejs` runtime rather than reimplementing browser automation.

### Enable browser automation

After Ego Lite and its `ego-browser` command are installed and onboarded:

```env
BROWSER_ENABLED=true
BROWSER_BACKEND=ego-lite
BROWSER_EGO_EXECUTABLE=ego-browser
```

Ego Lite currently documents macOS as its supported platform, with Windows/Linux on its roadmap. Morrow does not pretend an unavailable runtime exists: if `ego-browser` cannot be found, the provider fails closed with `BrowserBackendUnavailableError`. Browser automation remains disabled by default.

For compatibility-only use, `BROWSER_BACKEND=agent-browser` and `BROWSER_AGENT_EXECUTABLE=agent-browser` remain supported.

## Retry semantics

READ tools may advertise `retry_safe=true`. COMMIT actions are forced to side-effect=true, retry-safe=false, explicit approval, and an idempotency key on approved execution. `UnknownExternalResultError` remains non-retryable.

## Non-goals

Gmail, Calendar, WhatsApp/Discord/Slack, unrestricted browser mutation, shell/code execution, full cross-provider taint propagation, autonomous scheduling, and persona learning remain outside v0.2.5.
