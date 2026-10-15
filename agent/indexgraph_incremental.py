"""Freshness detection and transactional incremental persistence for IndexGraph.

The first IG-3 slice performs bounded deterministic discovery/build, computes a
path/fingerprint delta against the persisted snapshot, and writes only changed graph
rows. File parsing is still a full scan in this slice; changed-file-only extraction
is a follow-up optimization and is reported explicitly by the API.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent.indexgraph import GraphNode, IndexGraphStore, IndexManifest
from agent.indexgraph_bootstrap import BootstrapPolicy, BootstrapReport, build_index


@dataclass(frozen=True)
class IncrementalReport:
    """Result of reconciling a desired graph with its previous snapshot."""

    manifest: IndexManifest
    changed_paths: tuple[str, ...]
    deleted_paths: tuple[str, ...]
    unchanged_paths: tuple[str, ...]
    inserted_or_updated_nodes: int
    deleted_nodes: int
    inserted_or_updated_edges: int
    deleted_edges: int
    full_scan: bool = True


def _file_fingerprints(nodes: list[GraphNode]) -> dict[str, str]:
    return {
        node.path: node.source_fingerprint
        for node in nodes
        if node.kind in {"file", "manifest"} and node.path
    }


def refresh_index(
    project_root: str | Path,
    *,
    store: IndexGraphStore | None = None,
    policy: BootstrapPolicy | None = None,
) -> IncrementalReport:
    """Refresh a graph snapshot and persist only changed rows in one transaction.

    Discovery and parsing currently use the deterministic full-scan builder. The
    persistence layer is incremental, while full_scan makes the remaining extraction
    limitation visible to callers and telemetry.
    """
    root = Path(project_root).expanduser().resolve(strict=True)
    index_store = store or IndexGraphStore(root)
    _previous_manifest, previous_nodes, _previous_edges = index_store.load_snapshot()
    previous = _file_fingerprints(previous_nodes)

    desired: BootstrapReport = build_index(root, policy)
    current = _file_fingerprints(list(desired.nodes))
    current_paths = set(current)
    previous_paths = set(previous)

    changed_paths = tuple(sorted(
        path for path, fingerprint in current.items()
        if previous.get(path) != fingerprint
    ))
    deleted_paths = tuple(sorted(previous_paths - current_paths))
    unchanged_paths = tuple(sorted(
        path for path, fingerprint in current.items()
        if previous.get(path) == fingerprint
    ))

    delta = index_store.apply_snapshot_delta(
        desired.manifest,
        desired.nodes,
        desired.edges,
    )
    return IncrementalReport(
        manifest=desired.manifest,
        changed_paths=changed_paths,
        deleted_paths=deleted_paths,
        unchanged_paths=unchanged_paths,
        inserted_or_updated_nodes=delta["inserted_or_updated_nodes"],
        deleted_nodes=delta["deleted_nodes"],
        inserted_or_updated_edges=delta["inserted_or_updated_edges"],
        deleted_edges=delta["deleted_edges"],
        full_scan=True,
    )
