# PRD — Morrow v0.2

**Status:** Draft — blocking decisions remain  
**Version:** 0.2  
**Last updated:** 15 August 2026  
**Source:** Restructured from Morrow v0.1 (14 August 2026)  
**Profile:** Standard + Agent + High-Risk  
**Product:** Morrow  
**Product form:** Private multi-agent group assistant  
**Primary LLM constraint:** DeepSeek is the default reasoning provider; provider integration MUST remain interchangeable  
**MVP channel model:** Private messaging group; product behavior MUST remain channel-agnostic so messaging adapters can be replaced without changing the product contract

> This PRD is the **intent authority** for Morrow. Tests/checks provide executable conformance evidence; code is the implementation reality. If they diverge, the divergence MUST be reported and resolved rather than silently normalized.

---

# 1. Problem / Current State

The desired product is not a single chatbot pretending to switch personas. Morrow is intended to behave like a small private AI team inside one group conversation, where several independent agents can own work, delegate, share relevant context, and act autonomously inside Morrow without forcing the user to repeatedly coordinate them.

The previous Morrow v0.1 document already defines extensive behavior and architecture, but it mixes:
- product requirements;
- architectural choices;
- implementation details;
- operational rules;
- rollout phases.

That makes the intent understandable to a human reader but creates avoidable ambiguity for an implementation agent.

No external market research, adoption metrics, or user-study evidence are provided in the source material. This PRD therefore does **not** invent them.

---

# 2. Desired Outcome

Morrow SHOULD feel like a private working team that happens to live inside a group chat.

A whitelisted user should be able to:
1. speak naturally without command syntax;
2. address a specific agent or let Morrow choose one owner;
3. give work to the system without manually coordinating every sub-step;
4. send supported files for analysis;
5. rely on agents to share important context without replaying the full conversation;
6. allow internal work to proceed automatically;
7. retain control over any externally visible, destructive, or account-modifying action.

---

# 3. Actors

## ACT-01 — Whitelisted Group User

A human whose stable platform identity is allowed to interact with Morrow.

For MVP, all whitelisted users have equal product permissions.

## ACT-02 — Manager Agent

Primary responsibility:
- prioritization;
- task management;
- scheduling;
- dependency management;
- progress coordination;
- delegation;
- workload coordination.

## ACT-03 — Marketing Agent

Primary responsibility:
- campaigns;
- positioning;
- customer insight;
- content strategy;
- market research;
- promotion planning;
- marketing performance analysis.

## ACT-04 — Advisor Agent

Primary responsibility:
- decision analysis;
- risk;
- trade-offs;
- recommendations;
- short-term and long-term impact.

## ACT-05 — External System / External Recipient

Any system or person outside Morrow affected by an external action, such as:
- email recipient;
- calendar;
- social platform;
- purchase/transaction target;
- external account/data store.

---

# 4. Goals

- **G-001** Morrow MUST support natural-language tasking inside a private group.
- **G-002** Each user message MUST resolve to one primary agent owner before delegation.
- **G-003** Agents MUST remain role-separated even when they use shared skills.
- **G-004** Agents MUST be able to create, update, delegate, hand off, and complete structured tasks.
- **G-005** Agents MUST share relevant decisions/context without receiving all raw conversation history from other agents.
- **G-006** Supported attachments MUST be understandable through appropriate native parsing, OCR, and/or visual understanding.
- **G-007** Internal work SHOULD proceed without repeated user approval.
- **G-008** External actions MUST remain under explicit user control.
- **G-009** Autonomous agent-to-agent activity MUST have hard loop and conflict limits.
- **G-010** The MVP MUST remain materially simpler than B.I.M.A-CORE.

---

# 5. Non-Goals

The following are **not part of Morrow MVP**:

- **NG-001 [not now]** large LangGraph-style orchestration graphs;
- **NG-002 [not now]** CrewAI orchestration;
- **NG-003 [not now]** vector-database memory as a default architecture;
- **NG-004 [not now]** semantic embedding memory / reranking;
- **NG-005 [not now]** dashboard;
- **NG-006 [not now]** Discord;
- **NG-007 [not now]** Obsidian integration;
- **NG-008 [not now]** image generation;
- **NG-009 [not now]** arbitrary code execution;
- **NG-010 [not now]** desktop automation;
- **NG-011 [not now]** heavy browser automation;
- **NG-012 [not now]** OSINT tooling;
- **NG-013 [not now]** stock-specific tools;
- **NG-014 [not now]** TTS;
- **NG-015 [not now]** complex RAG;
- **NG-016 [not now]** multi-database architecture;
- **NG-017 [post-MVP]** generic motivational proactive chat with no work context;
- **NG-018 [post-MVP]** proactive scheduler behavior beyond real active work/deadlines.

---

# 6. Capability Map

| Capability ID | Responsibility | Depends On |
|---|---|---|
| CAP-ACCESS | private-group access, whitelist, group allowlist | — |
| CAP-AGENTS | independent role agents and display identity | CAP-ACCESS |
| CAP-ROUTING | primary-owner and reply-aware routing | CAP-AGENTS |
| CAP-SKILLS | role skills and shared skills | CAP-AGENTS |
| CAP-TASKS | task lifecycle, dependency, retry | CAP-AGENTS |
| CAP-HANDOFF | delegation and ownership transfer | CAP-TASKS, CAP-AGENTS |
| CAP-MEMORY | role/shared memory and audit | CAP-AGENTS |
| CAP-FILES | attachment intake, document/image understanding | CAP-ROUTING |
| CAP-CHAT | bounded agent-to-agent discussion | CAP-HANDOFF, CAP-MEMORY |
| CAP-APPROVAL | user approval for external actions | CAP-ACCESS, CAP-TASKS |
| CAP-SAFETY | conflict handling, loop budget, deduplication, confinement | all relevant capabilities |

These capability IDs SHOULD remain stable even if implementation modules change.

---

# 7. Scope Boundary

## 7.1 In Scope for MVP

- private group interaction;
- whitelist and group allowlist;
- Manager, Marketing, and Advisor as independent agents;
- fixed internal role IDs with customizable display names;
- single-primary-owner routing;
- reply-aware routing;
- role-specific and shared skills;
- structured tasks;
- dependencies, retry, delegation, and handoff;
- role memory + shared memory + memory audit;
- bounded visible agent-to-agent chat;
- conflict detection that pauses automation;
- supported file/document/image intake;
- native document parsing when structure exists;
- OCR for scanned/text-image content;
- visual understanding for image semantics;
- explicit approval before external actions;
- at least the external-action approval path required by MVP acceptance;
- security controls required by Section 13.

## 7.2 Out of Scope for MVP

Everything in Section 5 plus:
- role-based human permission tiers such as Owner/Admin/Staff/Viewer;
- shared ownership of a single task;
- uncontrolled multi-agent fan-out for one message;
- automatic resolution of contradictory human instructions;
- global blanket approval for future external actions.

## 7.3 Must Not Change / Invariants

- **INV-001** One user message MUST have exactly one primary agent owner before any delegation.
- **INV-002** One task MUST have exactly one current owner.
- **INV-003** Internal role IDs MUST remain stable even when display names change.
- **INV-004** A role MUST NOT silently become another role merely because its model can answer the request.
- **INV-005** Role routing and skill routing MUST remain separate concepts.
- **INV-006** Agents MUST NOT receive the entire raw history of other agents by default.
- **INV-007** Shared active memory MUST represent the current accepted fact/decision, while superseded values remain recoverable through audit history.
- **INV-008** Attachment extraction MUST NOT automatically become permanent memory.
- **INV-009** Internal actions MAY proceed without user approval only while they remain internal and within the approved product boundary.
- **INV-010** Every external action MUST require explicit approval scoped to that proposed action.
- **INV-011** Conflicting human instructions MUST pause the affected automation rather than using “latest message wins”.
- **INV-012** Automatic agent discussion MUST be hard-bounded.
- **INV-013** The same task MUST NOT cycle back to an agent already recorded in its handoff chain.
- **INV-014** Morrow MUST NOT use one global request lock that blocks unrelated groups/sessions.
- **INV-015** User-supplied files MUST be treated as untrusted input.

---

# 8. Core User/System Flows

## FLOW-001 — Explicit Agent Addressing

1. Whitelisted user sends a message naming a role/display name that resolves unambiguously.
2. Morrow identifies the role ID.
3. That agent becomes the primary owner.
4. The agent responds or delegates as required.

## FLOW-002 — Implicit Routing

1. Whitelisted user sends a message without a decisive role mention.
2. Morrow evaluates available routing signals.
3. Exactly one agent becomes primary owner.
4. Other agents are not invoked in parallel merely because they are also relevant.
5. The owner MAY delegate later.

## FLOW-003 — Reply-Aware Routing

1. Morrow sends a message produced by an agent.
2. The backend retains the relationship between the platform message and agent identity.
3. User replies to that message without naming an agent.
4. The originating agent becomes the routing target unless a higher-precedence signal is defined by `OQ-001`.

## FLOW-004 — Internal Delegation

1. Current owner identifies work owned by another role.
2. Current owner delegates without asking the user for approval.
3. A handoff context is created.
4. Ownership moves to the new agent.
5. The new agent continues from the handoff context.

## FLOW-005 — File Intake

1. User attaches a supported file.
2. File intake detects actual format.
3. Morrow chooses native parsing, OCR, visual understanding, or a combination based on file structure and requested intent.
4. A structured extraction/description is produced.
5. The role router selects one primary owner.
6. The owner uses the extracted result.
7. Only relevant durable facts MAY later be written to memory.

## FLOW-006 — External Action

1. Agent determines that a task requires an action outside Morrow.
2. Agent proposes the exact action and parameters.
3. Morrow asks for explicit user approval.
4. On approval, only the approved action MAY execute.
5. On rejection, the action is cancelled.
6. Parameter changes after approval MUST follow the policy decided in `OQ-006`.

## FLOW-007 — Human Instruction Conflict

1. New instruction conflicts with an active instruction/task or another whitelisted user's instruction.
2. Morrow pauses the affected automation.
3. Morrow explains the conflicting instructions.
4. Morrow waits for a valid human resolution.
5. No conflicting task/memory overwrite occurs before resolution.

## FLOW-008 — Agent Discussion

1. An agent starts an automatic agent-to-agent thread for a real task/dependency.
2. Only allowed agents may participate.
3. Each message must add information, a decision, a question, an action, or dependency update.
4. Thread ends when work is resolved or the turn/agent budget is exhausted.
5. On budget exhaustion, status becomes `waiting_user`.

---

# 9. Requirement Registry

## 9.1 Access & Identity

- **REQ-ACC-001** Morrow MUST process messages only from whitelisted stable platform identities.
- **REQ-ACC-002** Morrow MUST enforce a group allowlist in addition to user identity checks.
- **REQ-ACC-003** Messages from unauthorized identities/groups MUST NOT enter normal agent processing.
- **REQ-ACC-004** All whitelisted users MUST have equal product permissions in MVP.
- **REQ-ACC-005** Whitelist identity MUST NOT depend on display name.

## 9.2 Agents

- **REQ-AGT-001** MVP MUST provide independent Manager, Marketing, and Advisor agent runtimes.
- **REQ-AGT-002** Internal role IDs MUST be `manager`, `marketing`, and `advisor`.
- **REQ-AGT-003** Display names MAY be changed without changing routing identity.
- **REQ-AGT-004** Each agent MUST retain its role instruction, role memory, task context, and skill eligibility independently.
- **REQ-AGT-005** Manager MUST delegate role-specific work instead of absorbing another role merely because it can answer.

## 9.3 Routing

- **REQ-RTR-001** Every processable user message MUST resolve to exactly one primary agent owner.
- **REQ-RTR-002** Morrow SHOULD use deterministic/fast routing for unambiguous explicit role mentions, replies to known agent messages, and known task ownership.
- **REQ-RTR-003** Morrow MUST use a smarter routing decision only when deterministic routing is insufficient.
- **REQ-RTR-004** Reply-aware routing MUST preserve the relationship between a Morrow message and its producing agent.
- **REQ-RTR-005** When multiple agents are relevant, Morrow MUST choose one owner rather than invoking all relevant agents in parallel.
- **REQ-RTR-006** Routing precedence across conflicting signals MUST follow the decision produced for `OQ-001`.

## 9.4 Skills

- **REQ-SKL-001** Morrow MUST support role-specific skills.
- **REQ-SKL-002** Morrow MUST support shared skills available to multiple roles.
- **REQ-SKL-003** Skill use MUST NOT change the agent's role identity.
- **REQ-SKL-004** Skill routing MUST occur after role ownership is established.
- **REQ-SKL-005** A skill SHOULD be loadable as a modular artifact with its own instructions and optional references.

## 9.5 Files & Attachments

Supported MVP formats:

`PDF, DOCX, XLSX, CSV, TXT, MD, PPTX, PNG, JPG/JPEG, WEBP`

- **REQ-FIL-001** Attachments MUST enter a shared file-intake capability before role-specific reasoning.
- **REQ-FIL-002** Morrow MUST detect file format rather than trusting only the filename extension.
- **REQ-FIL-003** Structured formats SHOULD use native structural parsing when available.
- **REQ-FIL-004** Spreadsheet content MUST NOT be OCRed when native workbook structure is readable.
- **REQ-FIL-005** A PDF with a usable text layer SHOULD use text extraction instead of OCR.
- **REQ-FIL-006** A scanned/no-text-layer PDF MUST fall back to page rendering plus OCR and/or visual understanding.
- **REQ-FIL-007** Image text extraction and broader visual understanding MUST remain distinct capabilities.
- **REQ-FIL-008** The system MAY use both OCR and vision when the user request requires textual and visual interpretation.
- **REQ-FIL-009** Original attachments MUST be stored separately from durable memory.
- **REQ-FIL-010** Extracted attachment content MUST NOT automatically become permanent memory.
- **REQ-FIL-011** Attachment processing failures MUST return a bounded error/escalation result rather than silently pretending extraction succeeded.

## 9.6 Memory

- **REQ-MEM-001** Each agent MUST have role-specific memory.
- **REQ-MEM-002** Morrow MUST provide shared memory for cross-agent durable context.
- **REQ-MEM-003** Handoff context MUST be available to the receiving owner.
- **REQ-MEM-004** Agent context MUST be assembled from relevant memory/task/handoff context rather than all raw system history.
- **REQ-MEM-005** Agents MAY write important internal memory without repeated user approval.
- **REQ-MEM-006** Durable-memory candidates include accepted decisions, deadlines, project status, relevant facts, constraints, tasks, dependencies, and handoffs.
- **REQ-MEM-007** Filler, transient acknowledgements, and irrelevant rejected brainstorming SHOULD NOT become durable memory.
- **REQ-MEM-008** When an accepted fact/decision is superseded, active shared memory MUST reflect the new accepted value.
- **REQ-MEM-009** Superseded memory values MUST remain available in an audit history outside normal context.
- **REQ-MEM-010** Memory audit MUST record enough provenance to determine what changed and which actor/agent caused the change.
- **REQ-MEM-011** Conflicting human instructions MUST NOT overwrite active shared memory until the conflict is resolved.

## 9.7 Task Lifecycle

Canonical MVP statuses currently retained from v0.1:

`todo, in_progress, blocked, done, cancelled`

- **REQ-TSK-001** Tasks MUST use structured storage separate from general memory.
- **REQ-TSK-002** Each task MUST have one current owner.
- **REQ-TSK-003** A task MAY have multiple dependencies.
- **REQ-TSK-004** Completed and cancelled tasks MUST leave the active-task context and move to archive/history.
- **REQ-TSK-005** A blocked task MUST trigger bounded dependency-recovery attempts rather than remaining passively blocked forever.
- **REQ-TSK-006** The default retry budget is three attempts unless revised by an approved decision.
- **REQ-TSK-007** An agent MAY reorder task dependencies when it has a concrete reason.
- **REQ-TSK-008** Any automatic dependency reorder MUST be announced in the group with the reason.
- **REQ-TSK-009** The exact retry→handoff→terminal-state sequence MUST follow the decision produced for `OQ-002` and `OQ-004`.

## 9.8 Delegation & Handoff

- **REQ-HND-001** Internal delegation MUST NOT require user approval.
- **REQ-HND-002** A handoff MUST transfer ownership rather than create shared ownership.
- **REQ-HND-003** A handoff MUST carry sufficient task context for the receiving agent to continue without requiring the user to restate the task.
- **REQ-HND-004** Chained handoff MAY involve multiple agents.
- **REQ-HND-005** Each task MUST track agents already attempted in its handoff chain.
- **REQ-HND-006** A task MUST NOT be handed back to an agent already present in its attempted-agent chain.
- **REQ-HND-007** When no eligible untried agent can progress the task, Morrow MUST escalate rather than loop.

## 9.9 Agent-to-Agent Discussion

- **REQ-CHAT-001** Agents MAY communicate visibly in the group when the conversation advances real work.
- **REQ-CHAT-002** Automatic threads MUST have an explicit thread identity and state.
- **REQ-CHAT-003** Automatic threads MUST enforce a maximum of four agent-to-agent turns for the initial MVP rule.
- **REQ-CHAT-004** Automatic threads MUST involve no more than three agents.
- **REQ-CHAT-005** Agreement-only/filler agent messages MUST NOT consume discussion turns.
- **REQ-CHAT-006** An agent message SHOULD only be emitted when it adds new information, a decision, an important question, an action, or a dependency update.
- **REQ-CHAT-007** After the automatic turn budget is exhausted without resolution, the thread MUST enter `waiting_user`.
- **REQ-CHAT-008** Repeat participation semantics MUST follow the decision produced for `OQ-003`.

## 9.10 Conflict Handling

- **REQ-CNF-001** If a new human instruction conflicts with an active task/instruction, Morrow MUST pause the affected automation and request resolution.
- **REQ-CNF-002** Morrow MUST NOT silently cancel, overwrite, or reverse an accepted instruction when a direct conflict is detected.
- **REQ-CNF-003** Conflicting instructions from two whitelisted users MUST NOT use “latest message wins”.
- **REQ-CNF-004** Resolution authority and accepted resolution syntax MUST follow `OQ-005`.

## 9.11 External Actions & Approval

- **REQ-EXT-001** Sending email or an external message MUST require explicit user approval before execution.
- **REQ-EXT-002** Calendar modification MUST require explicit user approval before execution.
- **REQ-EXT-003** Social-media posting MUST require explicit user approval before execution.
- **REQ-EXT-004** Purchase or transaction execution MUST require explicit user approval before execution.
- **REQ-EXT-005** Destructive external-data changes MUST require explicit user approval before execution.
- **REQ-EXT-006** External-account modification MUST require explicit user approval before execution.
- **REQ-EXT-007** Approval MUST be scoped to a specific proposed action and MUST NOT create a vague blanket authorization.
- **REQ-EXT-008** Rejected external actions MUST NOT execute.
- **REQ-EXT-009** If an internal dependency can only be solved through an external action, Morrow MUST pause that external step and request approval rather than treating it as an internal retry.
- **REQ-EXT-010** Approval replay/retry/parameter-change semantics MUST follow `OQ-006`.

## 9.12 LLM & Context Behavior

- **REQ-LLM-001** DeepSeek MUST be supported as the default reasoning provider for MVP.
- **REQ-LLM-002** Provider integration MUST remain replaceable behind an interchangeable provider boundary.
- **REQ-LLM-003** Manager, Marketing, and Advisor MUST operate as independent agent runtimes/conversations rather than one shared conversation with role prompts swapped in-place.
- **REQ-LLM-004** Agent context SHOULD include only relevant role instruction, skills, own memory, shared memory, active tasks, current handoff, and current message.

---

# 10. Edge & Failure Cases

- **EDGE-001** Unauthorized user sends a valid-looking command → ignore/do not enter agent processing.
- **EDGE-002** User replies to an agent but names another agent → behavior is blocked on `OQ-001`.
- **EDGE-003** Two agents are equally relevant to an ambiguous request → still choose one primary owner.
- **EDGE-004** Attachment extension and detected content disagree → treat as untrusted and use safe detection policy.
- **EDGE-005** Native parser fails on a supported document → return bounded failure/fallback path; do not fabricate extracted content.
- **EDGE-006** PDF has no usable text layer → OCR/vision fallback.
- **EDGE-007** Image contains both textual and visual design information → OCR + vision MAY both be used.
- **EDGE-008** Memory update conflicts with unresolved human instruction → do not overwrite active memory.
- **EDGE-009** Dependency cannot be solved after bounded attempts → follow approved retry/handoff/escalation contract.
- **EDGE-010** Agent-to-agent thread reaches turn budget → `waiting_user`.
- **EDGE-011** Handoff would return to an already attempted agent → reject handoff and choose another eligible path or escalate.
- **EDGE-012** External action parameters change after approval → follow `OQ-006`; do not assume old approval remains valid.
- **EDGE-013** Duplicate platform delivery/message is observed → deduplicate before creating duplicate tasks/actions.
- **EDGE-014** Two unrelated groups/sessions operate concurrently → one MUST NOT globally block the other.

---

# 11. Non-Functional Product Constraints

## Security

- **NFR-SEC-001** User-supplied files MUST be treated as untrusted input.
- **NFR-SEC-002** Attachment handling MUST enforce path confinement.
- **NFR-SEC-003** Attachment handling MUST use safe type/extension/content detection.
- **NFR-SEC-004** MVP MUST enforce an attachment-size limit; exact threshold is a technical release decision.
- **NFR-SEC-005** MVP MUST enforce rate limiting; exact thresholds are technical release decisions.
- **NFR-SEC-006** MVP MUST enforce external-action approval before side effects.
- **NFR-SEC-007** MVP MUST enforce agent-loop budgets.
- **NFR-SEC-008** MVP MUST perform message deduplication.
- **NFR-SEC-009** MVP MUST detect task/instruction conflicts before destructive automatic resolution.

## Reliability / State Integrity

- **NFR-REL-001** A task MUST have a single authoritative current owner.
- **NFR-REL-002** Memory audit MUST preserve superseded durable-state history.
- **NFR-REL-003** Automatic recovery MUST be bounded; no infinite retry or handoff loops.
- **NFR-REL-004** A failed tool/file operation MUST NOT be represented to the user as a successful result.

## Concurrency

- **NFR-CON-001** Request serialization MAY occur per group/thread where needed.
- **NFR-CON-002** Morrow MUST NOT use one global lock that blocks unrelated groups or sessions.

## Provider Portability

- **NFR-PORT-001** Product behavior MUST NOT depend on DeepSeek-specific conversational state in a way that prevents provider replacement.

## Performance

No response-time, throughput, or file-processing latency targets are defined in Morrow v0.1. They MUST NOT be invented in this PRD. Any required release targets should be added as explicit decisions later.

---

# 12. Acceptance Contract

| AC ID | Requirement(s) | Scenario | Expected Result | Verification Lane |
|---|---|---|---|---|
| AC-001 | REQ-ACC-001..003 | non-whitelisted user sends message | message does not reach normal agent processing | integration test |
| AC-002 | REQ-AGT-001..003 | user renames Manager display name | internal role remains `manager`; routing still works | integration test |
| AC-003 | REQ-RTR-001,005 | ambiguous request fits multiple roles | exactly one primary owner is selected | routing test |
| AC-004 | REQ-RTR-004 | user replies to known Marketing message | reply can be routed back using stored agent mapping | integration test |
| AC-005 | REQ-HND-001..003 | Manager delegates Marketing-owned work | no user approval requested; owner becomes Marketing; context is preserved | workflow test |
| AC-006 | REQ-HND-005..007 | task chain attempts Manager→Marketing→Manager | second Manager handoff is rejected and system chooses valid alternative/escalation | workflow test |
| AC-007 | REQ-FIL-003,004 | valid XLSX uploaded | workbook structure is read natively; OCR is not the primary reader | file integration test |
| AC-008 | REQ-FIL-005,006 | scanned PDF with no text layer | OCR/vision fallback is invoked and extraction result is surfaced honestly | file integration test |
| AC-009 | REQ-FIL-007,008 | poster image requires design + text analysis | visual semantics and extracted text are both available to owner | multimodal/manual test |
| AC-010 | REQ-MEM-008..010 | accepted launch date changes from A to B | active memory shows B; audit preserves A→B change provenance | state test |
| AC-011 | REQ-MEM-011, REQ-CNF-001 | conflicting human instruction arrives | task/memory change pauses until resolved | workflow test |
| AC-012 | REQ-TSK-004 | task becomes done/cancelled | task leaves active context and appears in archive/history | state test |
| AC-013 | REQ-TSK-005,006 | dependency remains blocked | no more than configured retry budget occurs before next approved recovery step | workflow test |
| AC-014 | REQ-CHAT-003,004,007 | automatic discussion cannot resolve work | thread never exceeds four agent turns/three agents and ends in `waiting_user` | thread-state test |
| AC-015 | REQ-CNF-003 | two whitelisted users conflict | system does not choose latest-message-wins | workflow test |
| AC-016 | REQ-EXT-001,007 | agent proposes sending email | no send occurs before approval scoped to that email action | side-effect integration test |
| AC-017 | REQ-EXT-008 | user rejects external action | action is cancelled and no side effect occurs | side-effect integration test |
| AC-018 | REQ-FIL-009,010 | attachment is analyzed | extracted content is not automatically written to permanent memory | state test |
| AC-019 | REQ-LLM-003,004 | Marketing responds after Manager handoff | Marketing receives relevant handoff/shared context without receiving all raw Manager history | context assembly test |
| AC-020 | NFR-CON-002 | two groups process independent requests | one group does not globally block the other | concurrency test |
| AC-021 | NFR-SEC-008 | duplicate platform event is delivered twice | duplicate processing does not create duplicate task/external action | integration test |
| AC-022 | REQ-EXT-009 | blocked task needs external action | system asks approval instead of treating external side effect as automatic retry | workflow test |

## Acceptance blocked by unresolved decisions

The following acceptance contracts MUST be added or finalized after the associated questions are resolved:

- **AC-PENDING-001** deterministic routing precedence → `OQ-001`;
- **AC-PENDING-002** retry→handoff→terminal state → `OQ-002`, `OQ-004`;
- **AC-PENDING-003** repeat agent participation in an automatic thread → `OQ-003`;
- **AC-PENDING-004** human conflict resolution authority → `OQ-005`;
- **AC-PENDING-005** external-approval replay/parameter-change behavior → `OQ-006`.

---

# 13. Approved Constraints to Carry into Technical Design

These items are retained from Morrow v0.1 as **technical constraints/decisions**, not expanded into product requirements here.

- **TC-001** Structured MVP data is intended to use SQLite.
- **TC-002** Original files remain in filesystem/object-style storage, separate from structured memory.
- **TC-003** MVP does not require a vector database.
- **TC-004** Structured document formats should use native readers where practical; exact libraries belong in the tech spec.
- **TC-005** Scanned documents/images require OCR and/or a vision provider; exact provider belongs in the tech spec.
- **TC-006** Messaging integration should sit behind an adapter boundary.
- **TC-007** LLM integration should sit behind a provider interface with DeepSeek as the default.
- **TC-008** Concurrency control should be scoped per group/thread rather than globally.
- **TC-009** Exact package/folder structure from v0.1 is guidance for the tech spec, not a product contract.
- **TC-010** Exact SQLite table/schema design from v0.1 is guidance for the tech spec, not a product contract.
- **TC-011** Exact parser-library choices from v0.1 are guidance for the tech spec unless later approved as hard constraints.

---

# 14. Decisions, Assumptions, and Open Questions

## 14.1 Decisions Carried Forward

- **D-001** Morrow is a private multi-agent group assistant.
- **D-002** Manager, Marketing, and Advisor are separate agents.
- **D-003** Role IDs are stable; display names are mutable.
- **D-004** One primary owner is selected before delegation.
- **D-005** Internal actions may execute automatically within scope.
- **D-006** External actions require explicit action-specific approval.
- **D-007** Whitelisted users have equal permissions in MVP.
- **D-008** User-vs-user conflict pauses automation.
- **D-009** Agent discussion is visible and hard-limited.
- **D-010** Memory is role-specific + shared + audit-backed rather than raw full-history sharing.
- **D-011** Structured files should use native structural readers; OCR is not a universal file reader.
- **D-012** Vision and OCR are separate capabilities.
- **D-013** DeepSeek is default, but the provider is replaceable.
- **D-014** MVP remains intentionally smaller than B.I.M.A-CORE.

## 14.2 Assumptions

- **A-001** The MVP acceptance scenario requiring an email action implies that at least one real external-action integration must exist before MVP is considered end-to-end complete.
- **A-002** Security thresholds such as attachment size and rate limits are implementation/release parameters and are not product values defined by v0.1.
- **A-003** The exact first messaging platform is a technical implementation choice as long as private-group behavior satisfies the PRD.

## 14.3 Blocking Open Questions

### OQ-001 [BLOCKING — routing]
When routing signals conflict, what is the precedence among:
1. explicit role mention;
2. reply context;
3. known task owner;
4. conversation context;
5. attachment content;
6. inferred user intent?

### OQ-002 [BLOCKING — task recovery]
After three retries fail, does Morrow:
- hand off immediately to the next eligible agent;
- escalate immediately;
- or use three retries **per agent** before handoff?

Define the complete recovery sequence and whether the retry budget is global or per owner.

### OQ-003 [BLOCKING — thread semantics]
What exactly does “no duplicate agent reply” mean?

Choose one:
- an agent may participate only once per automatic thread;
- an agent may participate again only when adding new material information;
- only duplicate/near-duplicate message content is forbidden.

### OQ-004 [BLOCKING — task state]
Is `failed` a persisted task status?

If not, what status represents a task after all automatic recovery/handoff options are exhausted while waiting for the user?

### OQ-005 [BLOCKING — multi-user authority]
When two equal-permission whitelisted users conflict, what constitutes an accepted resolution?

The current rule correctly pauses automation, but the authority to resume is not defined.

### OQ-006 [BLOCKING — external side effects]
Define approval lifecycle:
- one-shot or reusable for retry;
- whether changed parameters invalidate approval;
- duplicate-execution protection/idempotency;
- expiration, if any.

## 14.4 Non-Blocking / Technical Open Questions

- **OQ-007 [NON-BLOCKING-PRD]** Which messaging adapter is implemented first?
- **OQ-008 [NON-BLOCKING-PRD]** Which vision provider is used for MVP?
- **OQ-009 [RELEASE-BLOCKING-TECH]** Exact attachment-size limit.
- **OQ-010 [RELEASE-BLOCKING-TECH]** Exact rate-limit policy.
- **OQ-011 [RELEASE-BLOCKING-TECH]** Exact file-sniffing/path-confinement implementation.
- **OQ-012 [NON-BLOCKING-PRD]** Exact SQLite schema/index strategy.

---

# 15. Product Success / Validation

The source PRD defines functional end-to-end success scenarios but does not provide real adoption, satisfaction, retention, or productivity baselines.

Therefore:

- Morrow v0.2 MUST NOT invent product-success percentages.
- MVP implementation success is evaluated through Section 12 acceptance.
- Post-release product-success metrics SHOULD be defined only when the user has a real baseline or chooses explicit targets.

Potential metric categories may later include:
- repeated-task coordination effort;
- number of times the user must restate context;
- internal delegation success;
- external-action approval error rate;
- task completion rate;
- user intervention rate.

These are **candidate categories only**, not approved targets.

---

# 16. MVP Release Boundary

MVP is considered functionally complete only when the following capability groups pass acceptance:

1. access/whitelist;
2. independent agents;
3. routing;
4. skills;
5. task + dependency lifecycle;
6. delegation/handoff;
7. role/shared memory + audit;
8. file intake including native document parsing and scanned-PDF OCR path;
9. bounded agent-to-agent discussion;
10. conflict stop;
11. external-action approval with at least the end-to-end path required by acceptance;
12. security/concurrency guardrails.

The proactive scheduler/morning-follow-up behavior is **post-MVP**.

Detailed implementation order belongs in `prd-task-planner` / technical planning rather than this product contract.

---

# 17. Agent Execution Guardrails

An implementation agent working from this PRD:

## MAY

- inspect the repository and existing B.I.M.A-derived patterns;
- implement approved local code changes;
- create/update tests;
- run local tests/build/lint;
- propose technical design consistent with this contract.

## MUST

- preserve all `INV-*`;
- link implementation tasks to `REQ-*`;
- link verification evidence to `AC-*`;
- expose contradictions or missing decisions;
- keep external actions disabled until their approval path is explicitly tested;
- treat files as untrusted;
- avoid global locks that violate `INV-014`.

## MUST NOT

- silently resolve any `OQ-* [BLOCKING]`;
- add out-of-scope capabilities “while already touching the area”;
- refactor unrelated modules without a requirement/approved technical need;
- weaken or delete failing tests merely to obtain a green build;
- convert external actions into automatic internal actions;
- replace role separation with one shared conversation/persona-switching runtime;
- add vector memory or heavyweight orchestration merely for convenience.

## STOP — Scope Expansion Required

If implementation cannot satisfy an approved requirement without expanding product scope, stop the out-of-scope change and report:

```text
STOP: SCOPE EXPANSION REQUIRED

Blocker:
Why current scope is insufficient:
Minimal additional capability/surface:
Affected REQ/INV/AC:
Alternative that stays in scope:
Evidence:
```

---

# 18. Verification & Completion Evidence

Before any capability is declared complete:

1. linked requirement IDs must exist;
2. linked acceptance checks must pass;
3. no unresolved blocking question may be silently assumed;
4. diff/surface review must show no unrelated scope expansion;
5. state-transition behavior must be tested for tasks, handoff, conflict, and approval;
6. file-processing tests must include structured and scanned inputs;
7. duplicate-message behavior must be verified;
8. external-action tests must prove “no approval = no side effect”;
9. automatic-thread tests must prove the loop budget;
10. a fresh review SHOULD compare implementation behavior against the PRD rather than against the implementation author's description.

**DONE = requirements satisfied + acceptance evidence + regression checks + scope compliance + no hidden blocker.**

---

# 19. Change Log

## v0.2 — 15 August 2026

- restructured v0.1 into a traceable intent contract;
- added stable capability, requirement, invariant, NFR, acceptance, and open-question IDs;
- separated hard product/system constraints from implementation-level technical design;
- surfaced retry/handoff/failure contradiction;
- surfaced automatic-thread repeat-participation ambiguity;
- surfaced routing precedence ambiguity;
- surfaced equal-user conflict-resolution ambiguity;
- added external-action approval lifecycle as a blocking decision;
- added explicit agent STOP/scope-expansion protocol;
- added requirement→acceptance verification matrix;
- retained original MVP non-goals, role model, file-intake philosophy, memory model, internal/external authority split, and anti-loop principles.

---

# 20. Implementation Readiness

**Current verdict:** NOT YET APPROVED FOR AUTONOMOUS IMPLEMENTATION.

Implementation planning may begin for unaffected capabilities, but autonomous end-to-end execution MUST NOT guess answers to:

- `OQ-001`
- `OQ-002`
- `OQ-003`
- `OQ-004`
- `OQ-005`
- `OQ-006`

Once those six product contracts are decided, this PRD can move from **Draft** to **Approved**, then feed `prd-tech-spec` and `prd-task-planner`.
