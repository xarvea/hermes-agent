# IndexGraph IG-3 — Freshness and Incremental Indexing

## Objective

Detect source changes and deletions deterministically, reconcile the persisted graph in one SQLite transaction, and avoid rewriting unchanged graph rows.

## This implementation slice

- Uses the deterministic IG-2 provider to produce the desired graph.
- Compares indexed file and manifest paths by content fingerprint.
- Reports changed, deleted, and unchanged paths separately.
- Reconciles graph nodes and edges using transactional upserts and stale-row deletion.
- Validates the complete desired snapshot before mutating persisted state.
- Uses SQLite WAL, foreign keys, and the store connection lifecycle already established by IG-1.

## Explicit limitation

`refresh_index` currently invokes the full deterministic builder to calculate the desired graph. Persistence is incremental, but file discovery, reads, and extraction are still full-scan. The report exposes `full_scan=True` so callers cannot mistake this slice for changed-file-only parsing. A follow-up must add a cached per-file extraction layer and dependency-aware invalidation before IG-3 can be considered complete.

## Invariants

1. A failed validation must leave the previous snapshot intact.
2. Removed source files must not leave orphaned nodes or edges.
3. Repeated runs with unchanged source must not rewrite graph node or edge rows.
4. Changed source fingerprints must update the corresponding persisted records.
5. Source paths remain project-relative and are validated by the existing store.
6. The indexer must not execute project code or send source content to a model.

## Acceptance tests

- Initial refresh indexes all eligible files and passes SQLite integrity checks.
- A no-change refresh reports unchanged paths and zero graph-row writes.
- A changed file is updated and a removed file is deleted with dependent edges.
- Invalid delta input is rejected without changing the previous snapshot.

## Follow-up before IG-3 completion

- Persist per-file extraction outputs and policy/config fingerprints.
- Skip parsing unchanged files when the path set and extractor configuration are stable.
- Invalidate dependent import edges when files are added, removed, or renamed.
- Preserve a safe full-rebuild fallback when cache metadata is absent or invalid.
- Add scale tests for large repositories and concurrent refresh attempts.
