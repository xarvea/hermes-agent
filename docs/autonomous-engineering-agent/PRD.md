# Product Requirements Document — Autonomous Engineering Foundation (PR #1)

- **Document status:** Baseline PRD reconstructed from merged implementation and repository planning records
- **Version:** 1.0
- **Date:** 2026-10-15
- **Repository:** `xarvea/zivi`
- **Origin:** [PR #1 — feat: add autonomous engineering agent foundation](https://github.com/xarvea/zivi/pull/1)
- **Merge commit:** `57bf927fdad7f2ff2e01d43e9a59d703d4eb53c4`
- **Implementation head reviewed:** `cb238e5eff194bfb971dbcba1cd6d1ecdbd20b5c`
- **Product status:** Foundation merged; autonomous Engineering Team OS is **not production-certified**
- **Evidence rule:** This document distinguishes delivered behavior, approved architecture, and remaining work. A merge or green CI is not evidence that every roadmap phase is complete.

## 1. Executive summary

PR #1 established the first foundation for evolving the Hermes runtime fork into an evidence-driven autonomous engineering organization. The intended system accepts a goal, PRD, or repository and progressively coordinates research, planning, implementation, verification, recovery, and reporting—without requiring the user to manually prompt every safe next step.

The design is not a role-play chatbot or a collection of personas that only discuss work. Role outputs must affect persisted decisions, task dependencies, implementation, and independently verifiable outcomes.

PR #1 delivered system-prompt guidance, a software-development workflow skill, a bounded project-local SQLite task-ledger fallback, safe task-state resume context, focused behavioral tests, generated skill/documentation updates, runtime-audit/architecture records, and Docker CI changes that permit secret-free validation of fork pull requests. It also changed CI runner selection toward standard GitHub-hosted Ubuntu runners and disabled the cross-platform OS test workflow for this Linux/Ubuntu-focused fork.

The merge is a **foundation milestone**, not completion of the full autonomous engineering product. The runtime audit explicitly remains in progress, and native Kanban is the preferred durable task graph and dispatcher where available. The SQLite ledger is only a bounded fallback; both must never be authoritative for the same run.

## 2. Problem statement

Software-engineering work performed by a general-purpose agent commonly fails in ways that a successful single response cannot detect:

- Requirements, assumptions, acceptance criteria, and dependencies are not consistently formalized before implementation.
- Research may rely on stale or unsupported assumptions instead of versioned, source-backed evidence.
- Task state can be transient, ambiguous, or incorrectly resumed after an interruption.
- Parallel workers can overlap files, duplicate work, or disagree about which task state is authoritative.
- A model-generated completion claim can be mistaken for verified behavior.
- Retry loops and multi-agent discussions can consume unbounded time, tool calls, and cost.
- Prompt instructions alone cannot reliably enforce permissions, approval boundaries, workspace isolation, or secret handling.
- Existing runtime facilities may be duplicated by a new orchestration layer unless the integration points are audited first.

The product must address these problems through explicit contracts, durable state, runtime-enforced policy, bounded execution, and evidence-based verification—not through prompts alone.

## 3. Product vision and outcome

**Vision:** Given a sufficiently specified engineering mission, Zivi/Hermes can coordinate a small logical engineering organization and deliver reviewable, tested changes with an auditable trail of decisions and evidence.

The target operating loop is:

`Observe → Research → Plan → Decide → Execute → Verify → Recover/Report`

The system should automatically continue through safe, authorized, unblocked work. It must stop or mark work blocked when required evidence, permissions, human approval, or an external dependency is missing.

### 3.1 Target users

- **Project owner:** supplies the mission, constraints, risk tolerance, and approval authority.
- **Engineering director / CTO role:** coordinates technical direction, dependencies, and decisions within delegated authority.
- **Specialist roles:** product analysis, research, architecture, frontend/backend, domain engineering, security, QA, and DevOps/SRE.
- **Independent reviewer:** evaluates changed behavior and evidence separately from the implementation agent.
- **Operator:** inspects state, logs, CI, checkpoints, and recovery status.

Roles are capability contracts, not a requirement to run one permanent model/process for every role.

## 4. Goals and non-goals

### 4.1 Goals

1. Provide default-on, tool-gated guidance for end-to-end engineering workflows.
2. Convert a mission into scope, non-goals, acceptance criteria, dependencies, risk classification, and a verification plan.
3. Research changing technology using authoritative, current sources and record versions, dates, confidence, and uncertainty.
4. Persist task state, dependencies, transitions, and verification evidence in one authoritative backend per run.
5. Prevent task execution before dependencies are complete and prevent completion without required evidence.
6. Resume only from explicitly recognized local fallback state; never treat stored state as proof that an external action completed.
7. Enforce project-root path containment and reject mutation of foreign or unrecognized task databases.
8. Reuse existing runtime capabilities and policy mechanisms rather than introducing competing schedulers or weakening safeguards.
9. Make fork CI validation possible without exposing publishing secrets to untrusted pull-request code.
10. Make progress and readiness auditable through tests, CI results, decision records, and explicit unresolved items.

### 4.2 Non-goals

- A web UI or dashboard for Team OS in the initial phases.
- Replacing the Hermes runtime, model/provider system, memory, native delegation, Kanban task graph, or dispatcher without evidence of a concrete gap.
- A mandatory model/provider assignment for every role.
- A permanent worker process for every role or multi-agent discussion for trivial tasks.
- Unbounded background execution, unlimited retries, or hidden activity.
- Automatic production deployment, financial transactions, privileged signing/key use, or destructive/irreversible operations.
- Claiming zero defects, universal project compatibility, or production readiness solely from passing CI.
- Renaming all internal Hermes/Nousearch identifiers as part of PR #1; branding migration is a separate coordinated effort.

## 5. Scope delivered by PR #1

### 5.1 Engineering workflow guidance

- Added default-on system-prompt guidance for research, acceptance criteria, dependency-aware planning, implementation, verification, safe continuation, and evidence-based reporting.
- Updated prompt surfaces and snapshots to make the behavior visible across supported interaction surfaces.
- Added the `software-development/autonomous-engineering-agent` skill and generated skill documentation/catalog/sidebar references.

### 5.2 Bounded SQLite task-ledger fallback

- Added a standard-library SQLite ledger at `.engineering-agent/state.sqlite3`.
- Models tasks, dependencies, transitions/events, and verification evidence.
- Applies dependency gates and task-state invariants.
- Requires evidence before a task can be considered complete.
- Enforces project-root path containment.
- Identifies the local fallback backend explicitly.
- Refuses to mutate foreign, unrecognized, or non-local task databases.
- Resume context reads only explicitly marked local fallback state.

**Important architecture update:** PR #1 introduced the SQLite fallback before the runtime audit fully established native Kanban as the preferred durable graph/dispatcher. The accepted ADR-0001 now makes native Kanban preferred when available and retains this SQLite implementation only as a bounded fallback. A run must select exactly one authoritative backend; no dual-write or silent synchronization is allowed.

### 5.3 Runtime integration audit and architecture records

PR #1 added:
- `docs/autonomous-engineering-agent/ARCHITECTURE.md`
- `docs/autonomous-engineering-agent/TEAM_OS_PLAN.md`
- `docs/autonomous-engineering-agent/PHASE0_RUNTIME_AUDIT.md`
- `docs/autonomous-engineering-agent/PHASE0_ACTION_ENFORCEMENT_MATRIX.md`
- `docs/autonomous-engineering-agent/decisions/ADR-0001-native-kanban-task-backend.md`
- `docs/autonomous-engineering-agent/decisions/ADR-0002-role-dispatch-and-kanban-ownership.md`

These records define the control-plane boundary, known runtime seams, trust boundaries, the preferred task backend, role-dispatch ownership, phase order, and remaining audit work. They are design and audit artifacts; their existence does not prove every proposed integration is implemented or tested.

### 5.4 Focused tests

PR #1 added 17 focused behavioral tests covering:
- autonomous engineering prompt guidance;
- task-ledger invariants and dependency behavior;
- task database ownership and backend isolation;
- safe task-state resume.

The tests provide focused coverage, not end-to-end certification of the full Engineering Team OS.

### 5.5 CI and platform adjustments

PR #1 also changed repository CI:
- Replaced custom larger-runner labels with standard GitHub-hosted runner labels in the affected workflows.
- Set relevant Linux jobs to Ubuntu 24.04 and the ARM64 Docker matrix to the standard Ubuntu 24.04 ARM runner.
- Disabled the cross-platform `tests-os` workflow in this fork's CI pipeline to reflect the Linux/Ubuntu-only target.
- Added/adjusted guards so Windows ARM64 native acceptance is not falsely claimed when running on an x64 host.
- Allowed fork PRs to run secret-free Docker image build and integration tests.
- Kept image publishing restricted to trusted upstream pushes to `main`; fork PR build jobs must not receive publishing secrets.

These CI changes are operationally significant and should be evaluated separately from the autonomous-engineering feature when future platform support is reconsidered. Disabled tests are not passing tests.

## 6. Architecture and ownership boundaries

### 6.1 Hermes Runtime — capability provider

The existing runtime owns model/provider routing, conversation/session lifecycle, tools, terminal/browser execution, skills, memory, native delegation, platform adapters, and existing approval mechanisms.

**Requirement:** reuse existing seams. Do not duplicate a core tool, scheduler, or delegation system unless a concrete unmet requirement and tests justify it.

### 6.2 Engineering Team OS — control plane

The Team OS owns mission lifecycle, role contracts, planning, research records, structured meetings, decisions/ADRs, task coordination, budgets, policy decisions, verification contracts, checkpoints, recovery, and audit events.

It orchestrates runtime capabilities; it does not replace the model runtime or rely on prompt text as a security boundary.

### 6.3 Project workspace — delivery plane

The workspace owns source, tests, requirements, ADRs, threat models, CI configuration, artifacts, and delivery evidence. State must be isolated by explicit project root and profile.

### 6.4 Task backend and dispatcher

- Native Kanban is the preferred durable task graph and dispatcher when enabled.
- The project-local SQLite ledger is a bounded fallback for standalone environments where Kanban is unavailable.
- Exactly one backend is authoritative per project run.
- Native `todo_list` is a conversational projection, not a second durable source of truth.
- Kanban-backed runs must reuse the native dispatcher/Swarm; do not build a parallel scheduler.
- The fallback must not claim to provide distributed dispatch or cross-process recovery capabilities that it does not implement.

### 6.5 Role contracts

Each role must eventually define a stable ID/version, purpose and non-responsibilities, capability/toolset allowlist, typed input/output, evidence requirements, escalation conditions, budgets/timeouts/retry policy, and review/decision ownership. Unknown roles, invalid outputs, and permission-escalation requests must fail closed.

### 6.6 Context Survival Protocol and area-based subagent delegation

**Status: PROPOSED — accepted for planning; not yet implemented or benchmarked.** This is a future capability of the Engineering Team OS, not functionality delivered by merged PR #1. It must be implemented in a separate, reviewable change after the relevant runtime seams and policy enforcement have been verified.

#### Objective

Keep each model invocation focused on the minimum context needed for its current responsibility while preserving mission continuity across long-running tasks, compaction, delegation, worker failure, and process restart. Reduce peak context pressure and irrelevant-token consumption without assuming that delegation automatically reduces total token usage or cost.

#### Operating model

`Mission Controller → Context Manager / Survival Protocol → bounded specialist workers → authoritative task backend + evidence artifacts`

- **Mission Controller:** owns the mission goal, hard constraints, global priorities, task graph, final integration, and user-facing status. It delegates work but does not surrender mission-level authority.
- **Context Manager:** assembles a task-specific context from the mission brief, current task contract, relevant decisions, recent evidence, and targeted source retrieval. It excludes unrelated history and limits tool-output size.
- **Survival Protocol:** persists enough structured state to recover after context compaction, model-call failure, worker failure, or restart. A model-generated summary is a recovery aid, not the sole source of truth.
- **Area workers:** handle bounded work such as research, backend, frontend, security, or QA/CI when the task graph shows that specialization or parallelism is useful. Each worker receives only its task contract and necessary project context.
- **Evidence store/workspace:** holds source references, test output, diffs, and detailed artifacts. The main context carries concise summaries and stable references instead of repeatedly embedding full outputs.

#### Durable task and recovery contract

The minimum recoverable state should include:

1. Mission and project/profile identifiers, root path, current objective, hard constraints, and acceptance criteria.
2. Authoritative task-backend identity, task IDs, dependency status, owner, and current state.
3. Accepted decisions/ADRs, assumptions, unresolved questions, blockers, and escalation requirements.
4. Last verified checkpoint, changed-file references, commands/checks actually run, results, and evidence locations.
5. Worker assignments, declared file/resource ownership, handoff status, and integration/review status.
6. Remaining budget, retry count, cancellation status, and next safe action.

Before resuming, the controller must reconcile this record against the actual workspace, task backend, artifacts, and external operation state. It must not infer completion from a worker spawn succeeding, a stale task flag, or a summary that lacks evidence. Non-idempotent actions require durable intent/result records and reconciliation before retry.

#### Context assembly and survival policy

- Retrieve first: load only the relevant task, decision records, source files, and evidence needed for the next action.
- Keep the mission brief, hard constraints, current task contract, active decisions, blockers, and next action in a compact, structured state.
- Store long logs, full tool outputs, and historical discussion as referenced artifacts; summarize them with provenance and retain exact output when required for debugging or audit.
- Use adaptive context thresholds as an initial configurable policy: begin compaction/retrieval when estimated context use exceeds **70%** of the available budget; at **85%**, prioritize recovery-critical state and stop unnecessary rescans. These are starting heuristics to validate experimentally, not universal model limits or benchmark results.
- Compaction must preserve constraints, decisions, task ownership, evidence references, unresolved risks, and the next safe action. It must not silently discard approval requirements or mark unverified work complete.
- If context reconstruction confidence is insufficient, critical state conflicts, or evidence cannot be reconciled, stop and mark the task blocked for investigation rather than guessing.

#### Area-worker contract

Each delegated task must declare: task ID and objective; owner/role; explicit in-scope and out-of-scope responsibilities; relevant inputs and references; permitted tools/capabilities; expected output schema; acceptance criteria; file/resource ownership; dependencies; time/token/tool-call/retry budgets; security/approval constraints; and escalation/stop conditions.

Each worker handoff must return a bounded, structured report containing:

- `summary`: concise result;
- `evidence`: source, diff, artifact, and test-result references;
- `findings`: facts, assumptions, and uncertainty clearly distinguished;
- `changes`: files or resources changed, if any;
- `verification`: checks actually executed and their outcomes;
- `blockers`: unresolved issues and required decisions;
- `next_action`: recommended safe continuation.

The controller validates the handoff against the task contract and acceptance criteria before integrating it. Invalid, incomplete, conflicting, or unsupported claims are rejected or sent back for bounded correction. The controller retains final integration and completion authority; workers cannot approve their own high-risk actions or independently redefine mission constraints.

#### Delegation and task ownership invariants

- Use area delegation only when specialization, isolation, or meaningful parallelism justifies the additional model calls and coordination overhead; simple tasks remain single-agent.
- Declare file/resource ownership before parallel writes. Prefer isolated worktrees or equivalent isolation where supported; serialize conflicting edits and integrate through review.
- Reuse native Kanban/Swarm/dispatcher when available. The selected authoritative backend remains exactly one per run; do not introduce a second scheduler or duplicate task ledger.
- Native `todo_list` remains a projection, not a competing durable state source.
- Delegated children do not independently own or mutate the parent’s Kanban lifecycle outside the accepted ownership contract.
- Apply least privilege, project/profile isolation, approval floors, cancellation, bounded fan-out, and per-worker/global budgets to all delegated work.
- Treat worker prompts, returned summaries, repository content, and tool output as untrusted input; none can grant permissions or override policy.
- A worker failure must yield a visible failed/blocked state with evidence. Recovery must be bounded and idempotent, not an unbounded respawn loop.

#### Efficiency hypothesis and measurement

The expected benefit is lower **peak per-invocation context** and less irrelevant context carried between tasks. Total input tokens, total cost, model-call count, and latency may increase because delegation introduces handoffs and duplicated setup. Therefore, do not claim that this protocol reduces cost until it is measured.

Benchmark single-agent and area-delegated execution on equivalent representative tasks, using the same acceptance criteria and comparable model/configuration. Record peak context/tokens per invocation, total input/output tokens, estimated or billed cost, model/tool-call count, wall-clock latency, completion and regression rate, recovery success, and human intervention. Include both a task suited to parallelism and a task where delegation is unlikely to help. Adopt delegation defaults only after the results show a justified trade-off.

#### Acceptance criteria for this future capability

- Recovery after compaction/restart reconstructs the current task and next safe action from durable state and evidence.
- No unverified completion, lost hard constraint, cross-project state leakage, or unauthorized action occurs in fault-injection and adversarial tests.
- Every worker is bounded by an explicit task contract, permissions, ownership, and resource budget.
- Conflicting writes are prevented or detected before integration; worker results require controller validation and independent review where risk warrants it.
- Exactly one task backend is authoritative throughout the run.
- Benchmarks report peak context, total tokens/cost, latency, model calls, quality, and recovery outcomes; no efficiency claim is made from peak context alone.
- Thresholds and delegation policies are configurable and validated against the supported models/runtime rather than hard-coded as universal facts.

## 7. Functional requirements

| ID | Requirement | Acceptance evidence |
|---|---|---|
| FR-01 | Interpret a mission into scope, non-goals, acceptance criteria, and measurable quality attributes. | Structured plan tied to the mission. |
| FR-02 | Research changing technology using current, authoritative sources. | Source URL/title, access date, version, finding, confidence, uncertainty. |
| FR-03 | Produce dependency-aware tasks with explicit owners, inputs/outputs, risk, budget, retry limit, and acceptance criteria. | Valid task graph; no task starts before dependencies complete. |
| FR-04 | Persist task transitions and events using one authoritative backend. | Backend selection recorded; no dual-write; event history is auditable. |
| FR-05 | Reject task completion without the declared verification contract and evidence. | Negative tests for missing/failed evidence. |
| FR-06 | Resume safely after interruption. | Reconcile actual workspace/artifacts; do not infer completion from spawn success or stale state. |
| FR-07 | Keep work inside the authorized project/profile boundary. | Traversal, symlink-escape, foreign DB, and cross-project isolation tests. |
| FR-08 | Execute within bounded concurrency, iteration, token/tool-call, time, and retry budgets. | Budget exhaustion produces a safe, visible stop/block state. |
| FR-09 | Preserve existing approval floors, hard blocks, capability intersections, and cancellation controls. | Negative/adversarial tests at actual action enforcement points. |
| FR-10 | Separate implementation from independent verification. | Reviewer/QA evidence and explicit disposition of findings. |
| FR-11 | Continue safe unblocked work without repeated user prompts. | End-to-end test demonstrating automatic progression and safe stop conditions. |
| FR-12 | Keep fork CI validation secret-free and publishing protected. | Workflow-policy tests and observed CI behavior. |
| FR-13 | Report actual verification outcomes honestly. | Passed/failed/blocked/skipped/not-verified matrix with evidence references. |
| FR-14 | Reconstruct task context safely after compaction, interruption, or restart. | Recovery tests reconcile durable state with actual workspace/artifacts; no inferred completion. |
| FR-15 | Delegate bounded work to area specialists only under explicit contracts and ownership. | Contract validation, permission/budget checks, conflict handling, and controller-validated handoffs. |
| FR-16 | Measure context efficiency without conflating peak context with total cost. | Comparable benchmark reports per-call peak context, total tokens/cost, latency, quality, and recovery. |

PR #1 only implements a subset of these requirements. The rest define the product target and subsequent phase acceptance criteria.

## 8. Security, trust, and safety requirements

1. **Untrusted content:** repository files, web pages, task titles, tool output, and meeting submissions cannot modify system policy, approvals, role permissions, or budgets.
2. **Least privilege:** role capabilities must be explicit and bounded by parent/runtime permissions. Unknown capabilities fail closed.
3. **Human approval:** required before production deployment/mutation, destructive or irreversible actions, financial actions, privileged signing/key use, broad access-control changes, publication of sensitive data, and materially ambiguous high-impact actions.
4. **Prompt is not enforcement:** authorization must be enforced at actual tool/action execution paths. A guardrail that detects loops is not a universal permission engine.
5. **Secret handling:** do not unnecessarily read secrets; never persist secret values in task state, prompts, meeting notes, logs, or fixtures. Evidence must be sanitized.
6. **Project/profile isolation:** resolve state from an explicit project root, enforce path containment, and test symlink/path escape and cross-profile cases.
7. **Independent review:** the implementation agent cannot be the sole approver of its own security-sensitive output.
8. **Bounded execution:** cap retries, meetings, fan-out, concurrency, and per-task/global resource budgets. Support cancellation and visible blocked states.
9. **Idempotency and reconciliation:** record durable intent/result for non-idempotent operations; reconcile actual state before retry or resume.
10. **CI trust boundary:** untrusted fork code may run secret-free validation, but must not publish packages or images or access release-signing credentials.

## 9. Non-functional requirements

- **Correctness:** explicit state transitions, dependency integrity, validated role outputs, and evidence-backed completion.
- **Security:** least privilege, fail-closed behavior, approval boundaries, isolation, secret-safe logging, and adversarial negative tests.
- **Reliability:** restart/resume, idempotency, reconciliation, bounded retries, and clear failure classification.
- **Auditability:** durable task events, decision records, evidence references, and explainable status.
- **Maintainability:** modular adapters and role contracts; preserve runtime facade and sibling-module conventions; avoid unnecessary core changes.
- **Performance/cost:** use a small logical roster; spawn specialists only when needed; cap model/tool budgets and parallelism.
- **Context survival:** preserve mission-critical state across compaction and restart; retrieve task-specific context instead of replaying full history; retain evidence provenance.
- **Delegation efficiency:** choose single-agent execution for simple tasks; use area workers only when measured quality/latency/cost trade-offs justify coordination overhead.
- **Portability:** current fork target is Ubuntu/Linux. Platform-specific tests disabled by policy must be reported as skipped/not applicable, not as passed.
- **Observability:** record task/meeting/role IDs, transitions, duration, budget use, failure class, and evidence references; redact sensitive payloads.
- **Recovery:** persisted state is a recovery hint; current working tree and real artifacts must be inspected before resuming.

## 10. Delivery phases and status after PR #1

Phase names and exit gates below follow the current accepted `TEAM_OS_PLAN.md`. The status is a conservative assessment from repository evidence as of 2026-10-15, not a claim that a phase is closed merely because PR #1 merged.

| Phase | Objective and exit gate | Status after PR #1 |
|---|---|---|
| **0 — Runtime audit and threat model** | Confirm AIAgent lifecycle, delegation, task authority, approval enforcement, project/profile boundaries, threat model, and test matrix; no guessed APIs. | **IN_PROGRESS / NOT VERIFIED.** Audit and action matrix exist, but open audit items remain, including full action-class enforcement mapping and focused runtime tests. |
| **1 — Workflow foundation and durable state** | Stabilize prompt guidance, skill, task ledger/read-only resume; verify path containment, state invariants, dependencies, evidence, bounded context, and secret safety. | **PARTIALLY DELIVERED.** Foundation and 17 focused tests merged. Complete phase acceptance evidence and focused test execution remain to be recorded. |
| **2 — Role registry and runtime integration** | Typed role contracts, capability/budget validation, explicit backend selection, Kanban/delegation integration, deterministic dispatch, and validated worker handoff contracts. | **NOT COMPLETE.** No claim of a complete role registry/backend adapter; Context Survival and area-worker contracts are proposed, not implemented. |
| **3 — CTO planner and research** | Structured requirements, source-backed research, alternatives, architecture, risks, and validated task graph. | **NOT COMPLETE.** Planning protocol is documented; automated planner behavior is not certified. |
| **4 — Meeting and decision protocol** | Bounded proposals/critique, conflict handling, decision ownership, ADR persistence, revisit conditions. | **NOT COMPLETE.** Protocol is specified; runtime behavior is not certified. |
| **5 — Execution orchestration** | Role-aware Kanban Swarm/dispatcher execution, isolation, checkpointing, safe auto-advance and resume. | **NOT COMPLETE.** Full end-to-end orchestration is still roadmap work. |
| **6 — Deterministic safety, QA, and recovery** | Runtime-enforced action policy, negative/adversarial tests, independent review, fault injection, bounded recovery. | **NOT COMPLETE.** Existing safety mechanisms are audited in part; universal action coverage is explicitly unresolved. |
| **7 — End-to-end certification** | Blank-repository build, existing-repository task, restart/resume, parallel conflict, tool failure, adversarial safety tests, and readiness report. | **NOT STARTED / NOT VERIFIED.** No end-to-end or production-readiness claim. |

A phase may be marked **COMPLETED** only when its exit gate is met and evidence is recorded. The repository's plan is the canonical source for changes to phase scope or acceptance criteria.

## 11. Verification and CI evidence for PR #1

The PR description records the following GitHub Actions results for implementation head `cb238e5eff194bfb971dbcba1cd6d1ecdbd20b5c`:

- **General CI:** PASS — [run #113](https://github.com/xarvea/hermes-agent/actions/runs/38697163752). Reported passing categories included Python test shards, JavaScript/TypeScript checks, Rust tests, lint/type/code-health checks, docs build, installer checks, supply-chain checks, and Docker script lint.
- **Docker build/integration:** PASS — [run #112](https://github.com/xarvea/hermes-agent/actions/runs/38697163644). Four variants reported passing: slim/amd64, slim/arm64, desktop/amd64, desktop/arm64. Publishing was skipped as expected for the PR.
- **Nix:** PASS — [run #112](https://github.com/xarvea/hermes-agent/actions/runs/38697163600), including `nix flake check`.
- **Skipped by design:** Desktop E2E and OS-specific tests for the Linux-only target; sandbox desktop image workflow.
- **Review caveat:** the CI review bot reported a system-prompt surface increase of approximately 431–432 tokens and stated that core approval was required. Passing CI did not itself satisfy that review requirement.
- **Local execution:** the PR record explicitly says tests were not executed locally in that session.

These are historical results recorded in the PR description, not a fresh CI query. They do not prove that the current `main` is green or that all later commits have passed.

### Verification policy going forward

- Use the repository-prescribed test runner: `scripts/run_tests.sh`.
- Run focused behavioral tests for each changed contract, then applicable lint/type/build/CI checks.
- Inspect the complete diff for unintended changes, secrets, and unrelated edits.
- Mark unavailable checks **NOT VERIFIED** and intentionally disabled checks **SKIPPED**.
- Separate implementation correctness, release readiness, and production readiness.

## 12. Risks and mitigations

| Risk | Impact | Mitigation / required evidence |
|---|---|---|
| Two authoritative task systems diverge | Lost, duplicated, or contradictory work | Explicit single backend per run; no dual-write; adapter contract tests. |
| Prompt guidance mistaken for security enforcement | Unauthorized tool/action execution | Map each action class to real enforcement points; adversarial negative tests. |
| Resume trusts stale state | Duplicate side effects or false completion | Inspect real artifacts; durable intent/result; reconciliation and idempotency. |
| Parallel workers edit shared files | Conflicts and regressions | Declared file ownership, worktree isolation where supported, serialized integration. |
| Unbounded retries/fan-out | Excessive latency and cost | Per-task/global budgets, bounded retries, cancellation, stop conditions. |
| Secret or project data leaks across context | Security/privacy incident | Sanitized evidence, explicit root/profile scoping, isolation tests. |
| Implementer self-certifies work | Defects pass unnoticed | Independent QA/security/reviewer gate. |
| CI platform coverage is reduced | Regressions on unsupported platforms may go undetected | State Linux-only support explicitly; never count disabled jobs as passing. |
| CI success is interpreted as production certification | Unsafe deployment or misleading claims | Phase exit gates and evidence-based readiness matrix. |
| Branding/runtime migration is mixed with engineering logic | Broad regressions and hard-to-review changes | Keep identity migration in separate, staged PRs with compatibility tests. |

## 13. Dependencies and constraints

- Existing Hermes runtime lifecycle, prompt-cache invariants, tool executor, approval floors, terminal guards, native delegation, Kanban database/dispatcher/Swarm, profile boundaries, and repository test harness.
- Native Kanban availability is runtime/profile dependent; unsupported modes require explicit behavior.
- The task backend adapter and role-dispatch boundary must be contract-tested before the scheduler is considered complete.
- Security policy must be enforced at action execution points, not merely represented in role prompts.
- Ubuntu/Linux is the declared target for this fork's current CI policy. Cross-platform support requires an explicit future decision and restored native test coverage.
- No direct push to `main`, merge, deployment, publishing, or release is implied by this PRD.

## 14. Decisions and open questions

### Accepted decisions

1. Keep Hermes as the underlying generic runtime; build Team OS as a control plane around existing capabilities.
2. Use structured, bounded decision workflows rather than open-ended multi-agent chat.
3. Prefer native Kanban as the durable task graph and dispatcher when enabled.
4. Retain the SQLite ledger only as an explicitly selected, bounded fallback.
5. Maintain exactly one authoritative task backend per run.
6. Reuse native dispatch and safety seams; do not introduce a competing scheduler.
7. Require independent verification and evidence-backed completion.
8. Require human approval for high-impact, destructive, financial, signing, and production actions.
9. Plan a Context Survival Protocol plus task-specific context assembly to preserve mission continuity while minimizing irrelevant context.
10. Plan area-based subagent delegation under explicit task, ownership, permission, evidence, and resource contracts; use delegation selectively and validate efficiency with benchmarks.

### Open items that block phase closure

- Design and implement the Context Survival state schema and Context Manager against verified runtime seams.
- Validate compaction/recovery thresholds and context assembly behavior with repeatable measurements.
- Implement bounded area-worker contracts, file ownership, handoff validation, and controller integration without duplicating Kanban/Swarm.
- Benchmark single-agent versus area delegation for peak context, total token/cost, latency, quality, and recovery before claiming efficiency gains.
- Complete the action-class inventory against enabled tools and actual handler call paths.
- Verify approval transport and subagent policy in CLI, gateway, and unattended execution contexts.
- Verify Kanban lifecycle/backend adapter contracts with focused tests.
- Verify role-dispatch ownership rules; Kanban tasks must not be independently owned by delegated children.
- Run focused tests in the prescribed isolated environment and record evidence.
- Complete the threat-model acceptance matrix.
- Add contract tests for task, delegation, approval, and persistence seams.
- Complete end-to-end certification before any production-readiness statement.

## 15. Definition of done for the overall product

The overall product is not production-ready until it demonstrates, for a declared supported scope:

- mission/PRD → source-backed research → plan → decision/ADR where warranted → task graph → implementation → independent verification → evidence-based report;
- safe continuation without repeated user prompting for authorized, unblocked work;
- durable task state and safe restart/resume;
- deterministic permission/approval enforcement, including adversarial bypass attempts;
- bounded execution, retries, cost, and concurrency;
- safe handling of secrets and project/profile boundaries;
- correct dependency scheduling and controlled parallel writes;
- independent quality/security review;
- project-appropriate tests and operational recovery checks;
- a readiness report listing passed, failed, blocked, skipped, and not-verified items plus residual risks.

## 16. Source of truth and research notes

This PRD was reconstructed on **2026-10-15** from repository evidence, prioritizing merged implementation and the current architecture records over assumptions.

Primary sources:
- [PR #1](https://github.com/xarvea/zivi/pull/1) — scope, merged head, CI evidence, caveats.
- [TEAM_OS_PLAN.md](./TEAM_OS_PLAN.md) — canonical product objective, architecture, phase order, exit gates, and global acceptance criteria.
- [PHASE0_RUNTIME_AUDIT.md](./PHASE0_RUNTIME_AUDIT.md) — observed runtime seams, integration implications, and unresolved audit items.
- [PHASE0_ACTION_ENFORCEMENT_MATRIX.md](./PHASE0_ACTION_ENFORCEMENT_MATRIX.md) — action enforcement inventory.
- [ADR-0001](./decisions/ADR-0001-native-kanban-task-backend.md) — accepted task-backend decision and consequences.
- [ADR-0002](./decisions/ADR-0002-role-dispatch-and-kanban-ownership.md) — role dispatch and Kanban ownership boundary.
- [ARCHITECTURE.md](./ARCHITECTURE.md) — architecture overview.
- [PR #1 changed-file list](https://github.com/xarvea/zivi/pull/1/files) — implementation and CI change surface.

**Research method:** repository planning and runtime-audit documents were inspected against the current `main`; PR #1 metadata, merge commit, changed-file list, and recorded CI evidence were checked. Runtime-specific claims are grounded in these repository sources. No external benchmark or unverified production claim is used. The phase status above is deliberately conservative and must be updated only when new test/CI/runtime evidence satisfies the relevant exit gate.
