# IndexGraph IG-3 — Freshness and Incremental Indexing

## Objective

Detect source changes and deletions deterministically, reuse extraction output for unchanged files, reconcile the persisted graph in one SQLite transaction, and avoid rewriting unchanged graph rows.

## Implemented behavior

- Performs bounded path discovery and reads eligible files to compare content fingerprints. This remains a full discovery/read scan in the current implementation.
- Reuses prior semantic nodes and edges for unchanged files when the extractor/configuration fingerprint is stable.
- Parses only changed/new files on ordinary content-only refreshes.
- When the eligible path set changes (add/delete/rename), re-extracts source files so import edges to newly available or removed targets are recalculated. This is a correctness-first invalidation strategy.
- When provider/configuration changes, rebuilds extraction output rather than trusting stale cached results.
- Reconciles graph nodes and edges using transactional upserts and stale-row deletion.
- Validates the complete desired snapshot before mutation.
- Uses SQLite WAL, foreign keys, and the store connection lifecycle already established by IG-1.

## Invariants

1. A failed validation must leave the previous snapshot intact.
2. A failed SQLite write must roll back all changes and preserve the previous snapshot.
3. Removed source files must not leave orphaned nodes or stale import edges.
4. Repeated runs with unchanged source must not reparse files or rewrite graph node/edge rows.
5. Content-only edits must reparse only the changed file while the path set and extractor configuration remain stable.
6. Adding/removing/renaming a path must invalidate import extraction so references cannot remain stale.
7. Source paths remain project-relative and are validated by the existing store.
8. The indexer must not execute project code or send source content to a model.

## Acceptance tests

- Initial refresh indexes all eligible files and passes SQLite integrity checks.
- A no-change refresh reports no parsed paths and zero graph-row writes.
- A content-only edit parses only the changed file.
- Removing an imported file reparses importers and removes the stale import edge.
- A changed file is updated and a removed file is deleted.
- Invalid delta input is rejected without changing the previous snapshot.
- An injected SQLite write failure rolls back and preserves the previous snapshot.

## Known limitation and follow-up

The implementation still walks eligible paths and reads bounded file content to fingerprint freshness; it does not yet avoid all I/O on a no-change run. Path-set changes intentionally trigger re-extraction of source files to preserve import graph correctness. Future optimization can add a reliable filesystem/Git change journal and dependency-indexed invalidation, but it must retain the safe full-rebuild fallback when cache metadata is absent or invalid.

The report exposes `full_scan=True` for full discovery/read scanning and `full_extraction_scan` to distinguish broad re-extraction from incremental extraction.
