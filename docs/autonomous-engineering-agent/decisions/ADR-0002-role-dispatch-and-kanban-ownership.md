# ADR-0002: Role Dispatch and Kanban Ownership Boundary

- Status: **PROPOSED IMPLEMENTATION CONTRACT**
- Date: 2026-10-14
- Scope: Engineering Team OS role dispatch on top of the existing Hermes runtime
- Related: [ADR-0001 — Native Kanban Task Backend](./ADR-0001-native-kanban-task-backend.md), [TEAM_OS_PLAN.md](../TEAM_OS_PLAN.md), [PHASE0_RUNTIME_AUDIT.md](../PHASE0_RUNTIME_AUDIT.md)

## Context

Hermes has two distinct concurrency/coordination mechanisms:

1. Native `delegate_task` creates isolated child AIAgent instances with inherited/intersected tool capabilities, child limits, and configurable approval behavior.
2. Kanban Swarm/dispatcher creates durable task graph entries and dispatches board-owned workers. Kanban task lifecycle is represented in the shared Kanban database and is reconciled by its dispatcher.

The repository's toolset contract states that `delegate_task` children are **not Kanban run owners**: the delegation schema strips/disables the Kanban toolset and runtime guards reject direct board mutations, even when parent Kanban environment variables are present. A delegated child therefore cannot be treated as the owner of a durable Kanban task.

## Decision

- Use Kanban Swarm/dispatcher as the execution authority for durable implementation tasks when Kanban is selected.
- Use native delegation for bounded, ephemeral analysis or proposal work only when the child does not need to own or mutate a Kanban task. Examples include independent research synthesis, architecture critique, or a read-only review.
- Do not try to make a delegated child a Kanban task owner by passing parent environment variables or by changing prompts. Do not weaken the runtime's Kanban-child restrictions.
- A role registry must separate **role identity and output contract** from **execution backend and tool permissions**. A role name alone never grants capabilities.
- For Kanban-dispatched workers, map the role to an approved Hermes profile and skill set. The effective capabilities remain bounded by that profile, the selected toolsets, workspace policy, and existing runtime guards.
- For delegate children, retain native capability intersection and child approval semantics. Unknown role mappings, unavailable profiles, or unsupported capability requests fail closed rather than falling back to a broader profile.
- One durable task has one execution owner and one authoritative task backend. Do not mirror Kanban task transitions into the local SQLite fallback ledger.
- Worker completion is accepted only through the owning backend's lifecycle and the task's verification contract. A delegation summary is evidence/input, not a substitute for a Kanban terminal state.

## Consequences

### Positive

- Preserves Kanban's existing dispatcher, ownership model, retries, run records, and recovery behavior.
- Avoids a competing scheduler and avoids dual-write task state.
- Keeps short-lived reasoning fan-out available without confusing it with durable execution.
- Makes role-to-profile mapping explicit and testable.

### Trade-offs

- Some roles may require profile/toolset configuration before they can be dispatched.
- A single workflow may use both mechanisms, but only for distinct responsibilities: delegated proposal/review tasks and Kanban-owned execution tasks. They must not share task ownership.
- A role that requires a capability unavailable in its approved profile must block with a specific reason rather than self-escalate.

## Required verification

- [ ] Contract test proving delegated children cannot mutate Kanban state, including attempts with inherited parent Kanban environment.
- [ ] Kanban Swarm integration test proving a dispatched worker owns and transitions its durable task through the existing lifecycle.
- [ ] Role mapping rejects unknown role, missing profile, unsupported capability, and disallowed toolset.
- [ ] Tests prove the role registry cannot broaden parent/session capabilities or bypass existing approval floors.
- [ ] Restart/recovery test reconciles a worker interruption without duplicate task ownership or dual writes.
- [ ] Verify current behavior with the repository-prescribed test runner; this ADR does not claim these tests have passed.

## Revisit conditions

Revisit only if repository evidence demonstrates a supported native delegation contract for durable Kanban task ownership, or if the existing dispatcher cannot satisfy a concrete Team OS requirement. Any change must preserve least privilege and single-source task authority.
