"""Freshness detection and changed-file extraction for IndexGraph.

Filesystem discovery and fingerprinting remain bounded full scans, but syntax/import
extraction is reused from the previous validated graph for unchanged files. If the
path set changes, all source files are re-extracted so imports to newly added or
deleted targets cannot remain stale.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from agent.indexgraph import (
    GraphEdge, GraphNode, IndexGraphStore, IndexManifest, IndexStatus,
    utc_now,
)
from agent.indexgraph_bootstrap import (
    BootstrapPolicy, BootstrapReport, MANIFEST_NAMES, SOURCE_SUFFIXES,
    _add_relationships, _build_structure, _collect_files, _fingerprint,
    _source_revision, build_index,
)
import json


@dataclass(frozen=True)
class IncrementalReport:
    """Result of reconciling a desired graph with its previous snapshot."""

    manifest: IndexManifest
    changed_paths: tuple[str, ...]
    deleted_paths: tuple[str, ...]
    unchanged_paths: tuple[str, ...]
    parsed_paths: tuple[str, ...]
    inserted_or_updated_nodes: int
    deleted_nodes: int
    inserted_or_updated_edges: int
    deleted_edges: int
    full_scan: bool = True
    full_extraction_scan: bool = False


def _file_fingerprints(nodes: list[GraphNode]) -> dict[str, str]:
    return {
        node.path: node.source_fingerprint
        for node in nodes
        if node.kind in {"file", "manifest"} and node.path
    }


def _config_fingerprint(policy: BootstrapPolicy) -> str:
    return _fingerprint(json.dumps({
        "provider": "builtin-deterministic", "version": "1",
        "max_files": policy.max_files, "max_file_bytes": policy.max_file_bytes,
        "max_total_bytes": policy.max_total_bytes,
        "excluded_dirs": sorted(policy.excluded_dirs),
        "text_suffixes": sorted(policy.text_suffixes),
    }, sort_keys=True).encode())


def _build_incremental_snapshot(
    root: Path, policy: BootstrapPolicy,
    previous_manifest: IndexManifest | None,
    previous_nodes: list[GraphNode], previous_edges: list[GraphEdge],
) -> tuple[BootstrapReport, tuple[str, ...], bool]:
    eligible, excluded, unsupported, file_data, errors = _collect_files(root, policy)
    project_id, _project_node, nodes, edges, path_nodes, fingerprints = _build_structure(
        root, file_data,
    )
    current_paths = set(file_data)
    previous_fingerprints = _file_fingerprints(previous_nodes)
    changed_paths = {
        path for path, fingerprint in fingerprints.items()
        if previous_fingerprints.get(path) != fingerprint
    }
    previous_paths = set(previous_fingerprints)
    path_set_changed = current_paths != previous_paths
    config_fingerprint = _config_fingerprint(policy)
    config_changed = (
        previous_manifest is None
        or previous_manifest.config_fingerprint != config_fingerprint
        or previous_manifest.provider_id != "builtin-deterministic"
        or previous_manifest.provider_version != "1"
    )
    # Adding/removing/renaming paths can change import resolution for unchanged
    # files, so invalidate all source extractors in that case.
    force_all = config_changed or previous_manifest is None or path_set_changed
    if force_all:
        parse_paths = set(file_data)
    else:
        parse_paths = set(changed_paths)

    previous_package_nodes = {
        node.id: node for node in previous_nodes
        if node.kind == "package" and node.path in file_data
        and node.path not in parse_paths
        and previous_fingerprints.get(node.path) == fingerprints.get(node.path)
    }
    nodes.extend(previous_package_nodes.values())
    valid_node_ids = {node.id for node in nodes}
    reused_edges = [
        edge for edge in previous_edges
        if edge.relation in {"imports", "declares_dependency"}
        and edge.source_path in file_data
        and edge.source_path not in parse_paths
        and previous_fingerprints.get(edge.source_path) == fingerprints.get(edge.source_path)
        and edge.from_id in valid_node_ids and edge.to_id in valid_node_ids
    ]
    edges.extend(reused_edges)

    if parse_paths:
        parse_data = {path: file_data[path] for path in sorted(parse_paths)}
        _add_relationships(
            root, parse_data, project_id, nodes, edges, path_nodes, fingerprints,
        )

    unsupported_paths = tuple(sorted(set(unsupported)))
    bounded_errors = tuple(errors[:100])
    status = IndexStatus.PARTIAL if bounded_errors or unsupported_paths else IndexStatus.READY
    manifest = IndexManifest(
        project_id=project_id, canonical_root=str(root),
        source_revision=_source_revision(root),
        provider_id="builtin-deterministic", provider_version="1",
        status=status, discovered_files=len(eligible), indexed_files=len(file_data),
        excluded_files=len(set(excluded)), unsupported_files=len(unsupported_paths),
        failed_files=len(bounded_errors), config_fingerprint=config_fingerprint,
        last_success_at=utc_now(), errors=bounded_errors,
    )
    report = BootstrapReport(
        manifest=manifest, nodes=tuple(nodes), edges=tuple(edges),
        indexed_paths=tuple(sorted(file_data)),
        excluded_paths=tuple(sorted(set(excluded))),
        unsupported_paths=unsupported_paths, errors=bounded_errors,
    )
    return report, tuple(sorted(parse_paths)), force_all


def refresh_index(
    project_root: str | Path,
    *,
    store: IndexGraphStore | None = None,
    policy: BootstrapPolicy | None = None,
) -> IncrementalReport:
    """Refresh the graph, reusing cached semantic edges for unchanged files.

    Discovery and bounded reads currently scan eligible paths to detect additions,
    deletions, and content changes. Parsing is incremental: unchanged files reuse
    prior extraction output unless path/config changes require dependency invalidation.
    The desired graph is validated before a single atomic delta transaction.
    """
    root = Path(project_root).expanduser().resolve(strict=True)
    selected_policy = policy or BootstrapPolicy()
    index_store = store or IndexGraphStore(root)
    previous_manifest, previous_nodes, previous_edges = index_store.load_snapshot()
    previous = _file_fingerprints(previous_nodes)

    desired, parsed_paths, full_extraction_scan = _build_incremental_snapshot(
        root, selected_policy, previous_manifest, previous_nodes, previous_edges,
    )
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

    delta = index_store.apply_snapshot_delta(desired.manifest, desired.nodes, desired.edges)
    return IncrementalReport(
        manifest=desired.manifest, changed_paths=changed_paths,
        deleted_paths=deleted_paths, unchanged_paths=unchanged_paths,
        parsed_paths=parsed_paths,
        inserted_or_updated_nodes=delta["inserted_or_updated_nodes"],
        deleted_nodes=delta["deleted_nodes"],
        inserted_or_updated_edges=delta["inserted_or_updated_edges"],
        deleted_edges=delta["deleted_edges"],
        full_scan=True, full_extraction_scan=full_extraction_scan,
    )
