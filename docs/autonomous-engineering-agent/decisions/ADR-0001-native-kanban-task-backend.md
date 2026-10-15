# ADR-0001: Reuse Native Kanban as the Team OS Task Graph Backend

- Status: **ACCEPTED**
- Date: 2026-10-14
- Decision owner: Engineering Team OS architecture
- Scope: durable engineering tasks, dependencies, worker dispatch, task events, and swarm handoffs in Hermes.

## Context

The first Team OS foundation added a project-local SQLite task ledger at `.engineering-agent/state.sqlite3`. A runtime audit then confirmed that Hermes already has a mature SQLite-backed Kanban subsystem:

- `hermes_cli/kanban_db.py` documents durable `tasks`, `task_links`, `task_comments`, `task_events`, `task_runs`, attachments, WAL, transactional writes, and compare-and-swap claim semantics.
- `hermes_cli/kanban_db_dispatch.py` owns worker dispatch, crash/stale/orphan handling, retries/failure accounting, concurrency, and dispatch lifecycle.
- `hermes_cli/kanban_swarm.py` already implements a durable dependency graph with a root/shared blackboard, parallel workers, a verifier gate, and a synthesizer. It explicitly avoids building a second scheduler.
- `tools/kanban_tools.py` exposes structured task operations with worker identity/ownership checks.
- The repository contribution rules require reusing existing runtime seams and avoiding duplicate schedulers/state systems without a demonstrated need.

Maintaining two independently writable task graphs would create conflicting status, dependency, and completion evidence, and would duplicate scheduling/recovery behavior.

## Decision

1. **Native Kanban is the preferred durable task-graph and dispatch backend** for Team OS runs where the Kanban subsystem is available and enabled.
2. Reuse Kanban's task links, events, runs, worker dispatch, workspace controls, and Swarm v1 topology. Do not implement a parallel scheduler or mirror task status into another database.
3. The Team OS owns higher-level planning artifacts—requirements, research, ADRs, meeting records, role contracts, risk registers, and verification policy—but task execution state remains authoritative in the selected backend.
4. The existing project-local SQLite ledger remains a bounded fallback for standalone projects/runtimes where Kanban is not enabled. Backend selection must be explicit and stable for the lifetime of a project run. Exactly one backend is authoritative for task status/dependencies; there is no silent dual-write or background synchronization.
5. When using the local fallback, the ledger provides durable task state but does not pretend to supply Kanban's multi-process dispatcher, worktree/workspace lifecycle, or cross-process recovery. The run must either use supported bounded local orchestration or report that required dispatch capability is unavailable.
6. Native `todo_list` remains a conversational display/projection, not a second durable source of truth.
7. Kanban workers and delegated children retain existing board/profile fences and ownership rules. Team OS roles cannot bypass native capability intersections, child restrictions, approval controls, or hardline command blocks.

## Consequences

### Benefits
- Reuses proven transactional persistence, task links, worker claims, run/event history, and dispatcher recovery.
- Avoids duplicating scheduling, worker lifecycle, crash recovery, and task-state synchronization.
- Enables human-visible Kanban/dashboard inspection while the team works.
- Keeps the Team OS provider-agnostic at the role/model layer while reusing Hermes' execution infrastructure.

### Costs and constraints
- Team OS must adapt its task graph to Kanban's task/status/dependency model and existing workflow transitions.
- Kanban is profile/home scoped and board resolution is fenced; project-to-board mapping must be explicit and must not leak tasks across profiles or projects.
- Kanban Swarm v1 topology may need additive extensions for role metadata, meeting gates, richer verification evidence, and project-run correlation. Extend existing schemas compatibly; do not fork the scheduler.
- Some runtime surfaces may not have Kanban enabled. Backend selection and unsupported-mode behavior must be explicit and tested.
- The local ledger implementation needs an adapter boundary and clear fallback semantics before it can coexist safely with Kanban.

## Rejected alternatives

### A. Make the project-local SQLite ledger the only task system
Rejected because it would duplicate native Kanban's durable graph, worker dispatcher, claims, event history, and recovery.

### B. Always dual-write Kanban and the project-local ledger
Rejected because partial writes and process interruption can make task state disagree; reconciliation becomes another scheduler problem.

### C. Remove the local ledger immediately
Rejected for now because the initial implementation already uses it for standalone resumability and focused tests. First define a backend interface and prove Kanban integration; only then decide whether the fallback can be retired safely.

## Required follow-up

- [ ] Define a typed task-backend interface and explicit backend selection for a project run.
- [ ] Map Team OS task states and dependency semantics to Kanban's workflow and links; do not assume the status names are identical.
- [ ] Extend Kanban Swarm only where needed for role IDs, project-run correlation, meeting/ADR gates, and verification evidence.
- [ ] Ensure all task transitions go through the selected backend; no dual-write.
- [ ] Test idempotency, claim contention, worker crash/restart, blocked dependencies, board/profile fencing, and cross-project isolation.
- [ ] Define behavior when Kanban is disabled or unavailable and ensure the fallback does not claim distributed dispatch.
- [ ] Update the architecture plan and Phase 0 audit to reference this decision.

## Revisit conditions

Revisit only if integration tests demonstrate that Kanban cannot satisfy a required Team OS invariant without unacceptable coupling, or if the runtime lacks the required Kanban capability on a declared supported surface. Any revisit requires evidence and a replacement ADR.
