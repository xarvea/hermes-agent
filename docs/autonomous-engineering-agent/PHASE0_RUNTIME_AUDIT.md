# Phase 0 — Hermes Runtime Integration Audit

## Status

- Phase: **IN_PROGRESS**
- Scope: read-only runtime inspection on `feat/autonomous-engineering-agent`
- Readiness: **NOT VERIFIED**
- This audit records confirmed repository contracts and implementation implications. It does not claim the runtime tests have been executed.

## Confirmed runtime seams

### AIAgent lifecycle and prompt invariants

- `run_agent.py` is the public AIAgent facade.
- `agent/agent_init.py::init_agent` assembles the agent; `agent/conversation_loop.py::run_conversation` runs turns, with phase-specific code under `agent/turn_*.py`.
- `agent/AGENTS.md` documents a synchronous loop with an iteration cap, an iteration budget, interrupt checks, and a one-turn grace call.
- Prompt caching is a hard invariant: system prompt/toolsets are stable for the conversation; mid-turn context changes must use supported user/tool-result paths, not mutate the cached system prompt.
- Agent-level tools such as `todo_list` and `memory` are intercepted by `agent/tool_executor.py` through `agent/inline_tool_executors.py` before ordinary registry dispatch.

**Implication:** Team state must be injected through a supported startup/resume seam and/or tool results. The scheduler must respect existing iteration budgets and interrupts rather than inventing a competing unbounded loop.

### Native delegation

- `tools/delegate_tool.py` builds child `AIAgent` instances with isolated conversation context and terminal task/session state.
- Native delegation supports single goals and batches; configured concurrency defaults to 3 in the documented contract.
- Native child roles are currently `leaf` and `orchestrator`, not business-specialist roles. `leaf` is the default; an orchestrator's recursive delegation is controlled by configuration and spawn-depth limits.
- Child toolsets are intersected with the parent's available toolsets. Blocked tools/toolsets are stripped; children do not gain capabilities unavailable to the parent.
- Optional worktree isolation exists for local Git-backed workspaces and is disabled by default.
- Per-child `max_iterations`, concurrency, spawn depth, and timeout settings already exist. Timeout defaults and semantics are progress/inactivity based, not a hard global project deadline.
- Background delegation is process-local. The documented contract says durable work across process restart requires a different persistence mechanism; a background delegation result alone is not durable workflow state.

**Implication:** Use native delegation for execution workers, but build the Team OS scheduler and persistent task/meeting state outside the child process lifecycle. Do not assume native delegation already supplies CTO/product/security role semantics or crash-resumable orchestration.

### Existing authorization and terminal guards

- `tools/approval.py` owns dangerous-command approval state and shared human-decision flow.
- `tools/approval_floors.py` applies hard blocks and user-defined deny rules before permissive approval modes; those blocks explicitly cannot be bypassed by YOLO or `approvals.mode=off`.
- `tools/terminal_tool_guards.py` contains pre-execution checks such as workdir validation and background/lifecycle guidance.
- `agent/tool_executor.py` applies tool scope, plugin pre-hooks, argument checks, and agent guardrails before dispatch.
- Subagent dangerous-command approval is not automatically inherited from the parent thread; its behavior is controlled through explicit delegation configuration, and opt-in auto-approval is a material safety setting.

**Implication:** Reuse the existing authorization and command-guard paths. Before adding a Team OS policy layer, map every action class to the current enforcement point and identify uncovered operations. Prompt instructions are not an enforcement boundary. Any new gate must not bypass, weaken, or duplicate existing hardline blocks.

### Existing task surfaces

- Native `todo_list` uses an in-memory, revisioned `TodoStore` attached to an agent. It is useful for conversational task display but is not, by itself, durable cross-session project state.
- Hermes also exposes Kanban task tools and dispatcher-owned worker context. The repository guidance distinguishes dispatcher-owned workers and native delegation context.
- The current engineering foundation adds a project-local SQLite ledger at `.engineering-agent/state.sqlite3` for durable tasks, dependencies, transitions, events, and verification evidence.

**Implication:** Phase 2 must choose and document one authoritative source for durable engineering task state. Do not silently synchronize two independently writable task databases. The native todo can be a projection/view. If the Kanban dispatcher is selected as the authority, implement an explicit adapter and define which fields/events the SQLite ledger owns; otherwise retain SQLite as authority and integrate through a narrow, tested adapter. The decision is pending evidence from the complete Kanban persistence/lifecycle path.

### Repository contribution constraints

- Root `AGENTS.md` says Hermes capability should primarily be added through skills/plugins and existing seams; core tools have a high bar and must have a concrete consumer.
- `tools/AGENTS.md` requires tests to exercise tool handlers through the registry for dispatch contracts and calls out real-import tests for approval/security boundaries.
- `tests/AGENTS.md` requires `scripts/run_tests.sh`, not bare `pytest`, with the repository's isolated test environment.
- New behavior must preserve profile isolation, prompt-cache invariants, and the project's facade/sibling-module conventions.

**Implication:** Prefer extending the existing delegation, inline tool, task/kanban, approval, and test seams. Avoid a new core tool unless the audit proves an existing surface cannot provide the required behavior.

## Initial threat model

| Threat | Required control |
|---|---|
| Instructions embedded in repository files, web pages, task titles, tool output, or meeting submissions attempt to override policy | Treat as untrusted data; validate structured outputs; policy authority remains outside model-controlled text |
| Specialist worker receives broader capabilities than its task needs | Explicit role/tool capability contract; intersect with parent permissions; fail closed on unknown role/capability |
| Parallel agents edit the same files or shared API contracts | Workspace/worktree isolation where supported; task ownership and declared file boundaries; serialized integration/review tasks |
| Agent loops, retries, meetings, or fan-out consume unbounded time/tokens/cost | Per-task and global budgets, concurrency/spawn-depth caps, bounded retries, explicit cancellation and stop conditions |
| Child finishes but parent/process restarts before result is recorded | Durable intent/result events, reconciliation on resume, idempotent task transitions; never infer completion from spawn success |
| Prompt asks to deploy, delete, sign, spend, or change access controls | Deterministic enforcement using existing guard/approval mechanisms plus explicit Team OS risk classification; human approval at the action boundary |
| Secrets leak through task state, prompts, meeting notes, logs, or test fixtures | Do not read secrets unnecessarily; redaction and bounded sanitized evidence; no secret values in persisted records |
| Project/profile state leaks across workspaces or profiles | Resolve state from explicit project root; enforce path containment and profile scope; test cross-root and symlink escapes |
| Implementer self-certifies a broken or unsafe change | Independent QA/security/reviewer roles and evidence-backed acceptance gates |
| Native task surfaces diverge from the engineering ledger | Select one durable source of truth; adapters are explicit, idempotent, and contract-tested |

## Open audit items

- [ ] Read the complete Kanban persistence and dispatcher lifecycle; determine whether it should be the durable task authority or an adapter target.
- [ ] Map all tool execution paths that can mutate files, start background work, change config, access credentials, deploy, or initiate financial/privileged actions.
- [ ] Verify existing guardrail configuration, approval transport, and subagent policy under CLI, gateway, and unattended execution contexts.
- [ ] Confirm whether role/capability metadata can be passed through native delegation without changing its public contract.
- [ ] Run focused tests using `scripts/run_tests.sh` in the repository-prescribed test environment.
- [ ] Add contract tests for Team OS ↔ native delegation/task/approval seams before implementing the scheduler.
- [ ] Finalize the threat-model acceptance matrix and close Phase 0 only after evidence is recorded.

## Phase 0 exit criteria

Phase 0 remains open until the task authority, delegation mapping, approval enforcement points, project/profile boundaries, and test strategy are confirmed from code and relevant tests. A source-level read is not equivalent to runtime verification.
