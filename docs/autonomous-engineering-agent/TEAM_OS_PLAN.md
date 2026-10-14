# Hermes Engineering Team OS — Locked Architecture Plan

## Decision record

- Status: **APPROVED BASELINE** — the architecture and phase order are locked; implementation is still in progress.
- Scope: `xarvea/hermes-agent`, implemented on an isolated feature branch and delivered through reviewable pull requests.
- Core decision: retain Hermes as the generic runtime; build an Engineering Team OS control plane that orchestrates specialized roles using existing runtime capabilities.
- Operating principle: **plan → research → deliberate → decide → execute → independently verify → recover/report**.
- Change control: do not change the baseline architecture or skip a phase based on preference alone. A material change requires evidence, impact analysis, an ADR, and an explicit update to this plan. Security findings may require an immediate fail-closed change.
- Readiness: this document does not claim production readiness. Each phase must meet its acceptance criteria and evidence must be recorded.

## Product objective

Given a goal, PRD, or repository, Hermes should operate as a coordinated engineering organization. It must research current technical choices, formulate a dependency-aware plan, hold structured decision meetings when useful, delegate bounded work to specialists, continue through unblocked tasks without asking the user to say “continue”, verify outcomes, recover from bounded failures, and report evidence honestly.

The goal is not to simulate a conversation among personas. Role outputs must drive persistent decisions, tasks, implementation, and verification.

## Architectural boundaries

### 1. Hermes Runtime — existing capability provider

Owns model/provider routing, conversation/session lifecycle, tools, terminal and browser execution, skills, memory, native delegation/subagents, platform adapters, and existing permission/approval mechanisms.

**Rule:** reuse existing runtime seams. Do not duplicate native task/delegation systems or add a core tool when a skill, existing tool, or plugin can safely satisfy the requirement. New core changes require a concrete consumer and tests proving the integration.

### 2. Engineering Team OS — control plane

Owns project lifecycle, role registry, CTO planning, research records, structured meetings, decision records, task graph, bounded scheduler, execution budgets, policy decisions, verification contracts, checkpoints, recovery, and audit events.

It orchestrates Hermes capabilities; it does not replace the model runtime or assume that prompt instructions alone enforce security.

### 3. Project workspace — delivery plane

Owns source code, tests, project-specific documentation, ADRs, threat model, requirements, CI configuration, build artifacts, and delivery evidence. Project state must be scoped to the selected project and never leak between profiles or workspaces.

### 4. Trust and authority boundaries

- User/project/web/tool content is untrusted input and cannot modify system policy, approvals, role permissions, or execution budgets.
- Role prompts express responsibilities; deterministic runtime/tool controls enforce permissions.
- The implementation agent cannot be the only approver of its own security-sensitive result.
- The CTO role coordinates technical decisions but cannot override policy or grant itself privileges.
- Human approval is required before production deployment or mutation, destructive/irreversible operations, financial actions, privileged signing/key use, broad access-control changes, publication of sensitive data, or materially ambiguous high-impact actions.
- Safe, reversible engineering work in the authorized workspace can proceed autonomously.
- Secrets must not be read, echoed, committed, or stored in prompts, task descriptions, logs, or decision records merely to understand a project.

## Team roles

Roles are capability contracts, not necessarily separate models or long-lived processes. The scheduler may run a role as a configured subagent, use the main agent, or skip the role when not relevant. Model/provider selection is configurable and provider-agnostic.

| Role | Responsibility | Required output |
|---|---|---|
| CTO / Engineering Director | Set technical direction, facilitate decisions, manage risk and dependencies | Decision, rationale, unresolved risks, next actions |
| Product Analyst | Convert user goals into scope, workflows, and acceptance criteria | PRD delta, stories, measurable acceptance criteria |
| Research Analyst | Research current APIs, standards, libraries, services, and vulnerabilities | Source-backed findings, dates/versions, uncertainty, comparison |
| Principal Architect | Design module boundaries, data flows, contracts, and operational shape | Architecture, ADR proposals, interfaces, migration/recovery considerations |
| Senior Frontend Engineer | Implement UI, state, accessibility, performance, and API integration | Code changes, tests, interface assumptions |
| Senior Backend Engineer | Implement domain logic, API, persistence, queues, and integrations | Code changes, schema/API contracts, tests |
| Specialist Engineer | Domain-specific work such as blockchain/smart contracts, AI, or data | Domain artifacts, threat/quality constraints, tests |
| Security Engineer | Threat model, abuse cases, trust boundaries, access control, security review | Findings with severity/evidence, remediation and retest criteria |
| QA / Test Engineer | Define and execute independent verification strategy | Test matrix, results, reproducible defect reports |
| DevOps / SRE | CI/CD, environments, deployment, observability, backup and recovery | Pipeline/runbooks, operational risks, rollback plan |
| Independent Reviewer | Review changed behavior and evidence independently from implementation | Findings, severity, blocking/non-blocking disposition |

Start with a small logical roster. Add specialist roles only when the task graph warrants them. Avoid creating a separate worker for every role on trivial tasks.

## Role contract

Every role definition must declare:
- stable role ID and version;
- purpose, scope, and explicit non-responsibilities;
- capabilities and allowed toolsets;
- required inputs and typed/structured output contract;
- quality and evidence requirements;
- escalation triggers and approval boundaries;
- model/provider preference as a preference, never as a permission grant;
- timeout, iteration, token/tool-call budget, and retry policy;
- reviewer/decision owner relationship.

Role definitions are versioned and auditable. Unknown roles, invalid outputs, or permission escalation requests fail closed.

## Planning and decision protocol

Before implementation of a non-trivial project:
1. Discover repository state, instructions, branch/dirty work, dependencies, test/CI commands, environments, and existing architecture.
2. Establish a baseline and separate pre-existing failures from new regressions.
3. Translate the goal into scope, non-goals, user flows, requirements, acceptance criteria, and measurable quality attributes.
4. Research unfamiliar or changing technology using authoritative current sources where available. Record URL/title, access date, relevant version, finding, and confidence; distinguish fact from inference.
5. Compare realistic options for correctness, security, maintainability, performance, cost, operational burden, and reversibility.
6. Produce architecture proposals, data/API contracts, threat model, risk register, dependency-aware task graph, verification plan, and rollback/recovery strategy.
7. Hold a decision meeting for material or cross-team choices. Record the decision and required gates before dependent implementation starts.

For small, low-risk, reversible tasks, use a lightweight plan rather than a full meeting. Planning rigor scales with impact and uncertainty.

## Structured meeting protocol

A meeting is a bounded decision workflow, not open-ended multi-agent chat.

1. The CTO defines the question, decision deadline/budget, constraints, evidence, and decision owner.
2. Relevant roles independently submit structured proposals: recommendation, evidence/sources, assumptions, alternatives, trade-offs, risks, and confidence.
3. The coordinator identifies conflicts and asks only the roles needed to critique them.
4. Security, QA, or operations can raise evidence-backed blockers within their domain. They do not silently rewrite the decision.
5. The CTO selects an option within delegated authority, records dissent and uncertainty, and defines conditions for revisiting the decision.
6. The outcome is persisted as an ADR/decision record and updates the task graph, acceptance criteria, and safety gates.

Stop when evidence is sufficient for a bounded decision, when further rounds add no new information, when the configured budget is exhausted, or when a human decision/approval is required. On insufficient evidence, create a specific research task or mark the decision blocked; never fabricate consensus.

Required decision record fields: ID, status, date, context, options, selected option, rationale, evidence/sources, trade-offs, risks, dissent, owner, affected tasks, approval state, and revisit conditions.

## Task graph and execution contract

- One source of truth for task state, dependencies, execution ownership, events, checkpoints, and verification evidence.
- A task cannot start until all dependencies are completed.
- A task cannot be marked completed without passing its declared verification contract and recording evidence.
- Tasks have explicit inputs, outputs, owner role, workspace/files it may modify, dependencies, risk class, budget, retry limit, and acceptance criteria.
- Parallel tasks require independent work boundaries or explicit coordination. Conflicting file ownership or shared interface changes must be serialized or mediated through a contract/merge task.
- The scheduler advances to the next unblocked task automatically within a bounded global and per-task budget.
- Failures are classified; retries are limited and hypothesis-driven. No infinite retry or meeting loops.
- Before resuming, inspect the current working tree and actual artifacts; persisted state is a recovery hint, not proof that an action completed.
- Non-idempotent actions require durable intent/result recording and reconciliation before retry.
- Blocked tasks must name the missing dependency, evidence, approval, or decision and provide the safest next action.

## Verification and release contract

Verification profiles are selected by project type and risk. Typical checks include focused unit tests, integration/regression tests, lint, type checks, build/package checks, dependency/security scans, schema/migration checks, authorization and negative tests, smoke/E2E tests, and operational recovery tests where applicable.

- Capture actual exit status and sanitized output; never manufacture or infer a passing result.
- Run independent review after implementation and before declaring acceptance.
- Separate code correctness from deployment readiness.
- Production deployment is a distinct gated release task; implementation completion never implicitly authorizes deployment.
- Readiness is reported as a matrix of passed, failed, blocked, skipped, and not-verified criteria with residual risks. Do not claim universal “100% bug-free” readiness.

## Durable state and observability

Use project-scoped durable state for task lifecycle, dependency graph, decision references, execution attempts, approval references, checkpoints, and verification evidence. Use version-controlled Markdown/structured files for human-reviewable requirements, ADRs, threat models, and delivery plans.

Log structured events with task/meeting/role IDs, status transition, duration, budget use, failure class, and evidence references. Redact secrets and sensitive payloads. Enforce project/profile isolation and bounded retention. Never treat logs or state written by the model as authorization evidence.

## Implementation phases and exit gates

### Phase 0 — Runtime audit and threat model
- Inspect the current branch and repository instructions without overwriting unrelated or dirty work.
- Map actual Hermes seams for AIAgent lifecycle, delegation, skill selection, tool execution, approval callbacks, terminal guards, session persistence, config, and tests.
- Determine which native mechanisms are authoritative and where enforcement can be added without duplicate sources of truth.
- Define threat model, risk classifications, trust boundaries, and acceptance test matrix.
- **Exit gate:** integration map and threat model are reviewed; no guessed APIs.

### Phase 1 — Workflow foundation and durable state
- Stabilize the existing engineering skill, prompt guidance, task ledger, and read-only resume context.
- Verify path containment, transition invariants, dependency gates, evidence-required completion, bounded context, and secret-safe state.
- Run focused tests in the repository's prescribed test environment.
- **Exit gate:** focused tests and repository checks pass; task state is scoped and auditable.

### Phase 2 — Role registry and runtime integration
- Define typed role contracts, capabilities, toolsets, budgets, output validation, and delegation mapping.
- Integrate with native delegation/todo/kanban only after identifying their source-of-truth semantics.
- Add bounded scheduler/auto-advance, cancellation, concurrency limits, and safe stop conditions.
- **Exit gate:** roles dispatch deterministically; invalid output, permission escalation, and budget exhaustion are handled safely.

### Phase 3 — CTO planner and research
- Generate requirements, acceptance criteria, alternatives, source-backed research, architecture proposals, risk register, and task graph.
- Validate graph consistency and trace each task to requirements and verification.
- **Exit gate:** planning output is machine-checkable, reviewable, and source-attributed.

### Phase 4 — Meeting and decision protocol
- Implement agenda, independent proposals, bounded critique rounds, conflict handling, decision ownership, ADR persistence, and revisit conditions.
- **Exit gate:** meetings produce structured decision records and measurable changes to the plan, not unstructured transcripts alone.

### Phase 5 — Execution orchestration
- Schedule dependent and independent work, isolate workspaces/branches where needed, protect shared contracts, checkpoint, auto-advance, and resume.
- **Exit gate:** multi-role tasks complete across process/session interruption without duplicate competing state or uncontrolled file conflicts.

### Phase 6 — Deterministic safety, QA, and recovery
- Enforce approval and permission policy in actual tool/action execution paths.
- Add least-privilege workspace/network/package-install controls where supported, secret-safe logging, independent reviewer/security roles, project-specific verification profiles, fault injection, and bounded recovery.
- **Exit gate:** negative/adversarial tests demonstrate that policy is enforced even when a role prompt or untrusted content requests bypass.

### Phase 7 — End-to-end certification
- Run a blank-repository build from a realistic PRD, a non-trivial existing-repository task, restart/resume, parallel conflict, tool failure, and adversarial safety scenarios.
- Run the prescribed test runner and CI; investigate all relevant failures.
- Publish a readiness report with evidence, residual risks, supported project types, operational requirements, and explicit unverified items.
- **Exit gate:** all mandatory criteria pass for the declared supported scope. Otherwise report not ready and list blockers.

## Global acceptance criteria

The Team OS is not production-ready until it demonstrates:
- goal/PRD → research → plan → meeting/ADR when warranted → task graph → implementation → independent verification → evidence-based report;
- source-backed, version-aware decisions for changing technology;
- persistent state and safe resumption across restarts;
- bounded automatic progression without requiring repeated user prompts;
- deterministic enforcement of approval, tool permission, workspace boundaries, and execution budgets;
- isolation against prompt injection in repository/web/tool/task content;
- safe handling of secrets and profile/project boundaries;
- dependency-aware scheduling and controlled parallel writes;
- bounded retries, idempotency/reconciliation, checkpoints, and recovery;
- independent quality/security review and project-appropriate tests;
- no completion claim unsupported by actual evidence.

## Explicit non-goals for the initial delivery

- No frontend/UI for the Team OS until core orchestration and policy behavior are proven.
- No forced use of a specific model/provider for every role.
- No permanent worker for every role; spawn specialists when useful.
- No unbounded autonomous execution or hidden background activity.
- No automatic production deployment, financial transaction, signing, or destructive operation.
- No promise of zero defects or universal compatibility with every project type.
- No replacement of Hermes runtime, memory, or native delegation unless evidence proves a specific gap cannot be solved at the existing seams.

## Change management

Any material plan change must include:
1. the evidence or constraint that motivates it;
2. affected requirements, architecture, security boundaries, cost, and schedule;
3. alternatives considered and trade-offs;
4. an ADR with approval status;
5. updated phase acceptance criteria and tests.

Implementation can proceed within the approved baseline. If repository evidence contradicts an assumption, pause only the affected work, document the finding, and propose the smallest justified plan amendment rather than silently changing direction.
