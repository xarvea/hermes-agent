# IndexGraph — Technical Contract and Bootstrap Design

- **Status:** Proposed implementation contract; review required before runtime implementation
- **Version:** 0.1
- **Date:** 2026-10-15
- **Scope:** Per-project indexing, retrieval evidence, freshness, and safe integration with the Engineering Team OS
- **Parent requirements:** [PRD §6.7](./PRD.md#67-mandatory-per-project-indexgraph-and-retrieval-gate)
- **Product boundary:** IndexGraph is derived project metadata, not a task scheduler, authorization system, or source of truth.

## 1. Decision summary

Implement IndexGraph as a small internal contract with pluggable indexing providers. Do not make GitNexus, Graphify, a vector database, or any third-party service a mandatory runtime dependency in the first milestone.

The repository already contains an optional GitNexus Explorer skill. Reuse it as a documented optional provider/integration candidate, but do not execute its interactive web/tunnel workflow as part of routine indexing. Any provider must be invoked through a bounded adapter and must satisfy the same schema, provenance, isolation, and freshness contract.

The initial bootstrap should be deterministic and local-first:
1. Validate the canonical project root and project identity.
2. Inventory tracked and eligible untracked source/config/test files using repository ignore policy and explicit exclusions.
3. Extract reliable file, package/workspace, manifest, and supported-language import relationships.
4. Store an index manifest, graph records, coverage report, and source fingerprints under the project-local engineering state directory.
5. Return an explicit state and evidence references to the controller.
6. Expand symbol/call graph coverage only through verified language providers.

No model call is required to build the baseline graph. AI inference may enrich it later, but inferred edges must be labeled and cannot be treated as confirmed dependencies.

## 2. Goals and non-goals

### Goals
- Make a project-specific graph available before non-trivial code mutation.
- Give planners and subagents source-backed retrieval and impact evidence.
- Detect stale or incomplete indexing instead of silently trusting it.
- Support full rebuild and safe incremental updates with comparable results.
- Keep project state isolated, bounded, auditable, and reconstructible.
- Integrate with Context Survival and area delegation without adding a competing scheduler.

### Non-goals for v1
- Building a graph visualization UI.
- Requiring embeddings, a hosted graph database, or an external API.
- Replacing Git, language servers, compilers, test runners, or source review.
- Claiming complete call graphs for languages whose parser/provider has not been validated.
- Executing project scripts, installing dependencies, or starting services as a side effect of indexing.
- Using the graph itself to grant permissions or authorize a change.

## 3. Runtime and storage boundary

The controller owns the indexing lifecycle and calls an `IndexProvider` adapter. The provider parses and emits normalized records; a storage layer validates and persists them; retrieval returns records with provenance and freshness status.

Suggested initial location:
`<project-root>/.engineering-agent/indexgraph/`

This aligns with the existing project-local engineering state convention. The implementation must confirm that this directory is ignored by Git; if it is not, add a narrowly scoped ignore rule and test it. Never put generated graph data into tracked source folders or a global cross-project cache by default.

Suggested layout:
```text
.engineering-agent/
  state.sqlite3                 # existing bounded task-ledger fallback, if selected
  indexgraph/
    manifest.json               # schema/provider/source fingerprints/status
    nodes.jsonl                 # normalized node records
    edges.jsonl                 # normalized edge records
    coverage.json               # exclusions, unsupported files, parse errors
    checksums.json              # per-file fingerprints for incremental sync
```

The files above are a proposed logical layout, not yet an implemented storage format. Before implementation, compare JSONL files against a small SQLite index store for atomic updates and query patterns. Do not put index records into the task ledger or make either one a second task authority.

## 4. Contract types

The exact implementation may use dataclasses or Pydantic only if already justified by the runtime's dependency policy. The schema semantics below are normative.

### 4.1 Index manifest

Required fields:
- `schema_version`: explicit version for migrations/invalidation.
- `project_id`: stable identifier derived from canonical root plus repository identity where available; must not expose secrets.
- `canonical_root`: resolved project root used for all path containment checks.
- `source_revision`: current Git commit when available, plus working-tree fingerprint/status.
- `provider_id` and `provider_version`: deterministic extractor identity.
- `created_at`, `updated_at`, `last_success_at`.
- `status`: `READY`, `PARTIAL`, `STALE`, `FAILED`, or `NOT_INDEXED`.
- `coverage`: discovered, indexed, excluded, unsupported, and failed file counts.
- `config_fingerprint`: relevant index configuration, ignore rules, and provider settings.
- `errors`: bounded, sanitized error codes and paths; no raw secret-bearing payloads.

### 4.2 Node record

Required fields:
- `id`: stable ID derived from project ID, node kind, normalized path/symbol identity, and schema version.
- `kind`: initially `project`, `directory`, `file`, `package`, `manifest`, `symbol`, `test`, `api_route`, or `config` only when supported by a reliable extractor.
- `label`: bounded display name.
- `path`: project-relative POSIX path; never an absolute path in graph content.
- `range`: optional start/end line and symbol name.
- `source_fingerprint`: fingerprint of the source input used to derive the node.
- `provenance`: extractor ID/version and source location.
- `confidence`: `confirmed`, `inferred`, or `unknown`; deterministic parse facts are confirmed, model-inferred facts are never silently upgraded.
- `attributes`: allowlisted, bounded metadata; must not include environment values, tokens, credentials, private keys, or file contents by default.

### 4.3 Edge record

Required fields:
- `id`: stable edge ID from source node, relation, target node, and schema version.
- `from`, `relation`, `to`.
- `provenance`: source file/range and extractor.
- `confidence`: `confirmed`, `inferred`, or `unknown`.
- `source_fingerprint`: source fingerprint used for this edge.

Initial relations may include `contains`, `imports`, `declares_dependency`, `tests`, `configures`, and `references`. Only emit a relation when its provider can substantiate it. Never fabricate a call edge from name similarity.

### 4.4 Retrieval result

Every result returned to the planner/worker must include:
- node/edge IDs and labels;
- project-relative source paths and line/symbol ranges where available;
- provenance and confidence;
- index status and source fingerprint/revision;
- coverage warnings relevant to the result;
- a reason for retrieval (direct match, dependency neighbor, test relation, or explicit path lookup).

The controller must inspect source files directly for critical or high-impact claims. Index results are navigation and impact evidence, not proof that runtime behavior is correct.

## 5. Project identity, path safety, and exclusions

- Resolve the project root once and require every indexed path to remain within it after symlink resolution.
- Use a project-scoped namespace for all cache keys and records; do not use basename alone as identity.
- Default to Git-tracked files plus eligible untracked files, respecting repository ignore rules and explicit exclusions.
- Exclude by default: VCS internals, virtual environments, dependency/vendor trees, build output, caches, binary/large generated files, runtime state, and secret files such as `.env` (including variants) and private key material.
- Index configuration *structure* where useful, never secret values. Avoid reading ignored secret files merely to classify them.
- Enforce configurable file-size, total-byte, file-count, parse-time, memory, and output-size limits.
- Treat filenames, manifests, comments, and source contents as untrusted data. Indexing must not execute them or follow embedded instructions.
- Use atomic writes or transactional commits. Interrupted builds must not replace the last known-good index with a falsely READY partial index.

## 6. Bootstrap lifecycle

The controller-facing lifecycle should be a small state machine:

`NOT_INDEXED → DISCOVERING → BUILDING → READY | PARTIAL | FAILED`

At task boundaries, freshness evaluation may transition `READY → STALE → BUILDING → READY | PARTIAL | FAILED`.

Required operations:
- `discover(project_root, policy) -> ProjectDescriptor`
- `build(project_descriptor, provider_config) -> BuildReport`
- `check_freshness(project_root, manifest) -> FreshnessReport`
- `update_incremental(project_root, changed_paths, manifest) -> BuildReport`
- `query(project_id, query, filters) -> RetrievalResult[]`
- `validate(project_root, index) -> ValidationReport`
- `clean(project_root, project_id) -> CleanReport`

These are logical contracts, not existing APIs. Every operation must be bounded, cancellation-aware where possible, and return structured failures instead of swallowing exceptions.

### First-use flow
1. Discover root, Git state, applicable instructions, project manifests, languages, workspace/package boundaries, and supported providers.
2. Read ignore/exclusion policy without executing project code.
3. Build a temporary index and coverage report.
4. Validate paths, IDs, provenance, referential integrity, and source fingerprints.
5. Atomically publish the new index only after validation.
6. Return status, coverage, errors, and next recommended action to the controller.
7. Record the index identity/revision and coverage gaps in the durable task/survival state.

### Incremental flow
1. Detect changed, deleted, renamed, and added paths from Git/worktree state and per-file fingerprints.
2. Recompute affected nodes and all incident edges.
3. Re-evaluate workspace/dependency relationships if manifests or configuration changed.
4. Validate the candidate index and compare key invariants against a full rebuild in tests.
5. Atomically publish; otherwise preserve the last known-good data but mark it STALE.
6. Recheck freshness before the next mutation and before final impact/verification reporting.

Filesystem watchers may optimize detection but are not the sole correctness mechanism. Branch changes, interrupted indexing, parser/provider changes, and schema changes require explicit revalidation; structural/configuration changes may require a full rebuild.

## 7. Mandatory retrieval gate

Before the first non-trivial source mutation, the controller must produce an `IndexGateReport` containing:
- project ID and canonical root;
- manifest status, source revision/fingerprint, and freshness result;
- relevant nodes/edges and source references;
- candidate files and likely downstream impact;
- relevant tests/checks where known;
- coverage gaps and assumptions requiring direct source inspection;
- selected fallback or blocking reason if the graph is unavailable;
- planned ownership boundaries if delegation will edit the project.

The runtime/orchestrator must enforce the gate at the engineering workflow boundary. Prompt guidance alone is insufficient. This design does not yet identify a production hook that can universally prevent every arbitrary terminal/file mutation; Phase 0 runtime audit must establish the actual supported enforcement seam before claiming that all code changes are technically blocked without a gate.

Lightweight exceptions may be allowed for pure explanation, read-only inspection, or explicitly low-risk single-file work. The controller must record the exception and its rationale. High-impact/security-sensitive changes require a fresh index or an explicitly approved source-based fallback with direct inspection and review.

## 8. Provider strategy

### Provider contract
Each provider declares supported languages/file types, version, deterministic guarantees, limits, extracted node/edge kinds, coverage metrics, and known blind spots. Provider output is normalized and validated before storage.

### v1 provider order
1. **Built-in deterministic baseline:** file/directory structure, manifests/workspaces, and reliable import/dependency relations for explicitly supported formats.
2. **Existing optional integrations:** a GitNexus adapter may be evaluated because the repository already ships an optional GitNexus Explorer skill. Do not run its web UI, tunnel, or repository-mutating side effects for ordinary indexing.
3. **Future language providers:** add only with fixtures and differential validation. Do not claim universal symbol/call-graph coverage.

No new core dependency should be added solely for IndexGraph before proving the baseline's gaps and comparing maintenance, licensing, security, and platform support. If the current runtime cannot provide a trustworthy graph for a language, mark coverage PARTIAL and use the policy-approved fallback.

## 9. Context Survival and delegation contract

Survival state should retain only stable references and recovery-critical facts:
- project ID/root identity;
- index schema/provider version and source revision/fingerprint;
- manifest status and freshness result;
- relevant node/edge IDs, file references, and known coverage gaps;
- task contract, ownership, decisions, evidence, budget, and next safe action.

After compaction/restart, revalidate the root and index freshness before relying on these references. Workers receive only task-relevant graph neighborhoods and source references, not the full graph. A worker may propose index updates but may not mark the index READY or declare its own task complete; the controller validates and publishes updates.

IndexGraph does not own task state or scheduling. Reuse the selected native Kanban/dispatcher or the explicitly selected SQLite fallback, never both as authorities.

## 10. Verification plan

### Contract/unit tests
- Stable IDs across identical rebuilds; IDs change correctly when source identity changes.
- Schema validation rejects invalid node kinds, missing provenance, invalid edges, and unbounded attributes.
- Root containment and symlink escapes are rejected.
- Exclusions cover secrets, ignored files, generated output, binaries, and oversized files.
- Untrusted source content cannot trigger command execution or policy changes.
- Failed/interrupted builds preserve the last known-good index and expose STALE/FAILED status.
- Deleted/renamed files remove stale nodes/edges.
- Incremental output matches full rebuild on deterministic fixtures.
- Cross-project retrieval/cache isolation is enforced.
- Retrieval includes provenance, confidence, freshness, and coverage warnings.
- Retrieval gate runs before eligible mutation; exceptions are explicit and tested.
- Indexing and query budgets/timeouts are enforced.

### Integration fixtures
- Small Python project.
- JavaScript/TypeScript package/workspace.
- Mixed-language repository.
- Monorepo with internal packages.
- Repository with generated/vendor/secret-like paths.
- Missing Git metadata, dirty working tree, branch switch, rename/delete, parser failure, interrupted update, and corrupted index.

### Performance/effectiveness measurements
Record baseline build duration, incremental duration, graph size, indexed coverage, parse failures, query latency/relevance, context tokens per task, total task tokens/cost, task quality, and regression rate. Compare incremental indexing to full rebuild and compare gated retrieval against no-index baseline on the same tasks. Do not claim cost or quality improvement until measurements are repeatable.

## 11. Implementation stages and gates

- **IG-0 — Runtime seam audit:** locate actual project-root selection, file access, skill/task orchestration, ignore handling, and safe action gate. No code mutation until these seams are confirmed.
- **IG-1 — Schema and storage:** implement manifest/node/edge contracts, atomic persistence, validation, project isolation, and focused tests.
- **IG-2 — Deterministic bootstrap:** implement discovery and baseline provider; document supported formats and coverage limits.
- **IG-3 — Freshness/incremental sync:** changed/deleted/renamed file handling, branch/config invalidation, and full-rebuild equivalence tests.
- **IG-4 — Retrieval gate:** wire the contract into the actual engineering workflow boundary; prove it runs before code mutation without breaking normal read-only tasks.
- **IG-5 — Survival/delegation integration:** persist stable references, validate worker handoffs, and test restart/recovery.
- **IG-6 — Evaluation:** run security, failure-injection, correctness, performance, and cost benchmarks on the declared Ubuntu/Linux target.

Each stage is a separate reviewable checkpoint. Do not label IndexGraph “mandatory and enforced” until IG-4 has runtime evidence. Documentation alone is not enforcement.

## 12. Open decisions before runtime implementation

- Confirm which runtime boundary can reliably gate non-trivial code mutations across CLI and any supported gateway/unattended contexts.
- Choose atomic JSONL/manifest storage versus SQLite after measuring query/update patterns and recovery behavior.
- Declare the initial language/provider matrix from available parsers and fixtures.
- Decide whether GitNexus should be a supported optional provider or remain only a user-invoked exploration skill.
- Confirm the repository ignore rule for generated `.engineering-agent/indexgraph/` data.
- Define risk classification for the permitted degraded fallback and its approval path.
