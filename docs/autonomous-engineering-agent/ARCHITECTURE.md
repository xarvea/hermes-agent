# Autonomous Engineering Agent — Architecture and Delivery Plan

## Status

- Current phase: Phase 1 foundation
- Branch: `feat/autonomous-engineering-agent`
- Overall readiness: **NOT VERIFIED** — this is an incremental foundation, not a production certification.
- Runtime integration, CI execution, full agent-loop orchestration, and adversarial evaluation remain open.

## Objective

Turn Hermes from a capable general-purpose runtime into a reliable engineering agent that can take a goal or PRD and execute a complete, resumable engineering workflow without requiring a user to manually advance every phase.

The system must be evidence-driven. It may autonomously make bounded, reversible engineering decisions, but must stop for explicit approval on production deployments, destructive/irreversible operations, financial actions, and other high-impact actions.

## Architecture

Keep Hermes as the runtime and build a thin, modular engineering control plane at the edges.

| Layer | Responsibility | Source of truth |
|---|---|---|
| Runtime | Model, tools, terminal, browser, sessions, subagents | Hermes |
| Engineering workflow | Discover → research → plan → implement → verify → recover → report | Engineering skill + project plan |
| Task state | Tasks, dependencies, state transitions, event history, verification evidence | Project-local SQLite ledger |
| Project decisions | Requirements, architecture decisions, assumptions, risks, ADRs | Version-controlled project docs |
| Safety gates | Approval for destructive, production, privileged, or costly actions | Deterministic policy/tool permissions, not prompt text alone |
| Verification | Tests, lint, type checks, build, security checks, smoke/E2E checks | Actual command output and CI evidence |
| Observability | Structured task events, failure reasons, elapsed time, checkpoints | Ledger and sanitized logs |

The task ledger is deliberately not an execution sandbox, policy engine, or agent scheduler. It supplies durable workflow state; later phases must integrate it with the runtime and deterministic tool controls.

## Required execution loop

1. **Discover** — inspect the repository, current branch, dirty changes, project instructions, dependencies, tests, CI, and deployment shape.
2. **Research** — consult authoritative current sources for unfamiliar/changing APIs and security concerns; capture references and uncertainty.
3. **Plan** — define acceptance criteria, risks, architecture decisions, and a dependency-aware task graph.
4. **Gate** — classify operations by impact and require approval where policy says so.
5. **Implement** — make small, reviewable changes and use focused tests.
6. **Verify** — run independent checks; compare results with the baseline and acceptance criteria.
7. **Recover** — diagnose failures, try bounded fixes, checkpoint progress, and resume after interruption.
8. **Review** — inspect the diff and run a security/reviewer pass independent of implementation reasoning.
9. **Continue** — automatically choose the next unblocked task; do not stop for a “continue” prompt.
10. **Report** — mark completion only with evidence; otherwise report BLOCKED, FAILED, or NOT VERIFIED.

## Task ledger contract

- Database defaults to `.engineering-agent/state.sqlite3` under the selected project root.
- SQLite is configured with WAL, foreign keys, and a 10-second busy timeout.
- Every task status change is recorded in `task_events`.
- A task can start only after all dependencies are completed.
- A task cannot be completed without verification evidence.
- Completed tasks are terminal; reopening must be an explicit future workflow with an auditable event.
- The state path must remain inside the project root.
- Never store credentials, private keys, access tokens, or secret values in the ledger.
- Runtime database files are ignored by Git and should be backed up only when required by the project's recovery policy.

## Delivery phases

### Phase 0 — Repository and threat-model audit

- [x] Inspect repository structure and applicable engineering instructions.
- [x] Create an isolated feature branch; do not change `main`.
- [x] Identify the system-prompt guidance seam and project-local skill/task-state surfaces.
- [ ] Verify automatic skill selection and task continuation at runtime.
- [ ] Verify current tool permission and approval mechanisms.
- [ ] Define threat model and acceptance test matrix.

### Phase 1 — Workflow and durable state foundation

- [x] Add an end-to-end engineering workflow skill.
- [x] Inject default-on, tool-gated engineering guidance into the stable system prompt.
- [x] Add a standard-library SQLite task ledger with dependency gates and evidence-required completion.
- [x] Add runtime-state ignore rule.
- [x] Add focused automated tests.
- [ ] Run focused automated tests in the repository environment.
- [ ] Add task ledger CLI integration documentation and examples.

### Phase 2 — Runtime integration

- [ ] Prove when/how the skill is selected for ordinary engineering requests.
- [ ] Connect task state to the existing task/todo/delegation surfaces without duplicate competing sources of truth.
- [ ] Add resume-on-session-start behavior using persisted project state.
- [ ] Add explicit iteration/time/tool-call budgets and safe stop conditions.
- [ ] Preserve prompt-cache, message-role, profile-isolation, and tool registration invariants.

### Phase 3 — Deterministic safety and execution policy

- [ ] Enforce approval gates in the tool/action path, not just in the skill prompt.
- [ ] Add least-privilege workspace boundaries and explicit policy for network access, package installation, secrets, and production credentials.
- [ ] Ensure untrusted repository/web content cannot alter policy or approval state.
- [ ] Test destructive-command prevention and safe handling of secrets with adversarial cases.

### Phase 4 — Independent verification and recovery

- [ ] Add verification profiles per project type.
- [ ] Require real command results and capture sanitized evidence.
- [ ] Add failure classification, bounded retry, checkpoints, idempotency, and resume.
- [ ] Add reviewer/security checks and regression tests before completion.
- [ ] Add fault-injection tests for interruption, database contention, missing dependencies, and failed commands.

### Phase 5 — Certification

- [ ] Test from a blank repository using a realistic PRD.
- [ ] Test a nontrivial existing repository task with regression checks.
- [ ] Test prompt injection, secret exposure, path escape, unauthorized deployment, and destructive operations.
- [ ] Verify restart/resume and dependency scheduling.
- [ ] Run project CI and review all results.
- [ ] Publish a readiness report with residual risks and explicitly unverified items.

## Acceptance criteria

The engineering agent is not considered production-ready until it can demonstrate all of the following:

- Starts from a goal/PRD and produces a plan with testable acceptance criteria.
- Researches unfamiliar or changing technical choices and records sources.
- Maintains task/dependency state across process and session restarts.
- Automatically advances through unblocked work within a bounded execution budget.
- Does not claim completion when tests or required checks have not run.
- Requires approval for production, destructive, privileged, and costly actions.
- Does not expose secrets or follow instructions embedded in untrusted project/web content.
- Recovers from interrupted work without losing task state or repeating non-idempotent actions.
- Passes unit, integration, negative, security, and end-to-end tests relevant to the supported workflows.
- Reports remaining limitations rather than declaring universal “100%” readiness.

## Current known limitations

The skill and task ledger are a foundation only. They do not yet force automatic skill activation, run background jobs, sandbox terminal commands, enforce privileged-action approval, or prove an end-to-end autonomous build. Those require additional runtime integration and tests. Do not describe this branch as production-ready until the open acceptance criteria are satisfied.
