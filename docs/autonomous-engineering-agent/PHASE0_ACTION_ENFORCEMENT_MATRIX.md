# Phase 0 — Action Enforcement Matrix

## Status

- Status: **IN_PROGRESS — source review only**
- Branch: `feat/autonomous-engineering-agent`
- Purpose: map existing enforcement points before adding Team OS policy. This is not a claim that every action is gated or that the matrix has been runtime-tested.
- Source review is based on the branch's current source files; focused tests must confirm the call paths before Phase 0 can close.

## Enforcement map

| Action class | Existing enforcement seam | What the seam establishes | Team OS requirement / remaining proof |
|---|---|---|---|
| Terminal command execution | `tools/terminal_tool.py`, `tools/terminal_tool_guards.py`, `tools/approval.py`, `tools/approval_floors.py` | Pre-execution workdir/lifecycle guards and command approval flow exist. Approval floors document hard blocks and user deny rules before permissive approval modes. | Trace every terminal entry point through all guards; test dangerous-command, malformed-input, workdir, and unattended-context denial. Team OS must not bypass these gates. |
| Arbitrary code execution | `tools/approval.py` includes `check_execute_code_guard`; tool dispatch runs through `agent/tool_executor.py`. | A dedicated execute-code guard exists; generic tool dispatch is centralized. | Confirm all execute-code tools invoke the guard in CLI, gateway, cron, and delegated-child contexts. Fail closed if risk classification or approval transport is unavailable for a gated operation. |
| File mutation / patching | `agent/tool_executor.py` dispatch pipeline and the registered file/patch tools | Central tool dispatch and tool-scope checks are present. This alone does not prove every write is individually approval-gated. | Enumerate write-capable tool definitions and their actual handlers. Add project-root/worktree boundaries and negative tests; classify broad deletes, overwrites, and cross-root writes as high risk. |
| Background work / process lifecycle | `tools/terminal_tool_guards.py`; Kanban dispatcher lifecycle and worker state | Terminal lifecycle guidance and durable Kanban task/run records exist. | A successful spawn is not task completion. Reconcile child/run state after interruption; bound concurrency, runtime, retries, and cancellation. |
| Delegated workers | `tools/delegate_tool.py`, `tools/delegate_tool_config.py`, child-run helpers | Delegation has child-specific tool/capability inheritance and configurable approval callbacks; parent approvals are not automatically equivalent to child approvals. | Map business roles to existing child roles without broadening permissions. Unknown role/capability must fail closed. Verify approval inheritance and output validation for every runtime context. |
| Configuration / permissions | Config readers and existing approval/guard paths | Config and approval mechanisms exist, but a Team OS role prompt is not an enforcement boundary. | Identify tools that can change policy, credentials, profile settings, or permission configuration. Require explicit approval for policy weakening and privilege changes; test attempted bypass. |
| Deployment / infrastructure | Terminal and registered provider-specific tools, depending on environment | No universal Team OS deployment authorization gate is established by this source review. | Treat deployment and production mutations as separate gated tasks. Require explicit human approval at the action boundary; do not infer authorization from a plan or ADR. |
| Credentials / secrets | Credential resolution and provider/session mechanisms; tool-result sanitization | Existing runtime manages provider credentials and display sanitization in selected paths. This does not establish complete redaction of Team OS state or every tool result. | Never persist secret values in task state, meeting proposals, logs, or evidence. Audit read/write paths and test redaction with canary secrets. |
| Financial / signing / privileged external actions | Depends on registered tool/provider and terminal path | No universal gate for every possible external action is established. | Enumerate actual enabled tools for the active profile; unknown or newly registered high-impact actions must be denied until classified. Explicit approval is required for spending, signing, and irreversible privileged actions. |

## Trust and policy invariants

1. Repository content, web pages, task fields, meeting submissions, tool results, and model-generated plans are untrusted data. They cannot modify policy or grant permission.
2. A role's declared capabilities are a maximum policy envelope, not a grant that supersedes the parent's available tools or the user's approvals.
3. The effective capability set is the intersection of role policy, parent/session capabilities, project/workspace policy, and runtime tool availability.
4. Unknown role, unknown capability, malformed structured output, ambiguous risk class, and unavailable required approval transport must fail closed for gated operations.
5. Existing hard blocks remain authoritative even if permissive modes or model instructions suggest otherwise.
6. Exactly one durable task backend is authoritative per project run. The Team OS must not mirror task transitions into both Kanban and the local SQLite fallback.
7. Spawn/dispatch success is not completion. Completion requires the backend's terminal state plus the task's declared verification evidence.
8. Deployment, destructive data changes, signing, spending, privilege changes, and production mutations are separate approval boundaries. Planning or test success never authorizes them.

## Required tests before Phase 0 exit

- [ ] Terminal guard/approval call-path tests across interactive CLI, gateway, cron/unattended, and delegated child contexts.
- [ ] Execute-code guard is reached for every enabled execute-code tool.
- [ ] Write-capable tool inventory with project-root and worktree containment tests, including symlink/cross-root attempts where applicable.
- [ ] Deny/hardline policy cannot be bypassed by permissive approval modes.
- [ ] Child capability intersection and unknown-role/capability rejection.
- [ ] Missing approval transport fails closed for actions that require approval.
- [ ] Canary-secret redaction through task state, logs, meeting output, and tool evidence.
- [ ] Kanban lifecycle: create, claim, run, complete/review/block, retry/park, interruption/reconcile, and idempotent recovery.
- [ ] Tests run using repository-prescribed `scripts/run_tests.sh` environment; capture actual outcomes and relevant CI jobs.

## Phase 0 closure rule

This matrix is an audit artifact, not runtime proof. Close Phase 0 only after each applicable enforcement path has a source trace and a passing focused test (or a documented, explicitly accepted limitation), the task-backend and delegation contracts are tested, and the threat-model acceptance matrix is evidence-backed.

## Existing test suites mapped to the enforcement matrix

The following are **candidate existing tests**, identified by source-tree inspection. Their existence is not proof that they pass on the current branch. CI outcomes and focused runtime execution must be recorded before closing Phase 0.

| Matrix concern | Existing test candidates | What still must be established |
|---|---|---|
| Terminal destructive-command approval and hard blocks | `tests/tools/test_approval.py`, `tests/tools/test_approval_deny_rules.py`, `tests/e2e/core/security/test_approval_boundary.py`, `tests/agent/test_terminal_approval_batch.py` | Confirm current-head results and trace each enabled terminal entry point, including unattended and delegated contexts. |
| Execute-code authorization and unattended denial | `tests/tools/test_execute_code_approval_cluster.py`, `tests/tools/test_execute_code_lifecycle_guard_deadline.py` | Confirm all registered execute-code surfaces reach the guard and fail closed when approval cannot be obtained. |
| Gateway approval boundaries | `tests/gateway/test_approval_boundary.py`, `tests/gateway/test_approval_prompt_redaction.py` | Confirm approval state remains session-scoped and sensitive payloads are redacted on every relevant output path. |
| Delegated child isolation from Kanban mutation | `tests/tools/test_delegate_kanban_isolation.py`, `tests/hermes_state/test_delegate_child_routing_inheritance.py` | Preserve the runtime fence; prove a delegated child cannot claim, complete, delete, or otherwise mutate a parent-owned Kanban task even with inherited environment variables. |
| Worker profile/tool scope and write guard | `tests/hermes_cli/test_kanban_worker_terminal_scope.py`, `tests/hermes_cli/test_kanban_write_guard.py` | Verify workspace containment and profile/credential isolation in the supported execution environments. |
| Durable graph, dependency gate, interruption/recovery | `tests/hermes_cli/test_kanban_swarm.py`, `tests/gateway/test_kanban_reconcile_orphans.py`, `tests/e2e/core/kanban/test_kanban_dispatcher_restart.py`, `tests/e2e/core/kanban/test_kanban_worker_sigkill.py` | Confirm lifecycle behavior and idempotent recovery on the current head; dispatch success must not be treated as verified task completion. |

### Team OS-specific gaps not closed by the existing runtime tests

- [ ] Explicit per-run backend selection and a negative test proving no task transitions are written to both Kanban and the SQLite fallback.
- [ ] Typed role/capability validation: unknown roles, unknown capabilities, malformed role output, and capability escalation must fail closed.
- [ ] Secret-canary tests covering the Team OS ledger, role/meeting records, structured task evidence, and logs.
- [ ] An action inventory tied to actual registered tool handlers, including file writes, patching, browser mutations, config/permission changes, deployments, signing, spending, and external publication.
- [ ] Current-head test evidence for all applicable candidates above, including skipped tests and environment limitations.

**Phase 0 remains IN_PROGRESS.** These mappings narrow the verification work; they do not satisfy the exit gate by themselves.
