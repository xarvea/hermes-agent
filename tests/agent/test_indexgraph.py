"""Contract tests for the project-local IndexGraph schema and store."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent.indexgraph import (
    Confidence,
    GraphEdge,
    GraphNode,
    IndexGraphStore,
    IndexManifest,
    IndexStatus,
    project_id_for,
    stable_id,
)


def _manifest(root: Path, *, status: IndexStatus = IndexStatus.READY) -> IndexManifest:
    return IndexManifest(
        project_id=project_id_for(root),
        canonical_root=str(root.resolve()),
        source_revision="a" * 40,
        provider_id="builtin-baseline",
        provider_version="1",
        status=status,
        discovered_files=1,
        indexed_files=1,
        last_success_at="2026-10-15T00:00:00+00:00",
    )


def _node(root: Path, path: str = "src/main.py", *, node_id: str | None = None) -> GraphNode:
    return GraphNode(
        id=node_id or stable_id("node", path),
        kind="file",
        label=Path(path).name,
        path=path,
        source_fingerprint="sha256:" + "b" * 64,
        extractor_id="builtin-baseline",
        extractor_version="1",
        confidence=Confidence.CONFIRMED,
    )


def _edge(source_path: str = "src/main.py", *, from_id: str, to_id: str) -> GraphEdge:
    return GraphEdge(
        id=stable_id("edge", from_id, "imports", to_id),
        from_id=from_id,
        relation="imports",
        to_id=to_id,
        source_path=source_path,
        source_fingerprint="sha256:" + "c" * 64,
        extractor_id="builtin-baseline",
        extractor_version="1",
    )


def test_project_id_is_stable_for_same_root(tmp_path):
    assert project_id_for(tmp_path) == project_id_for(tmp_path)
    assert project_id_for(tmp_path, "repo-a") != project_id_for(tmp_path, "repo-b")


def test_stable_id_is_deterministic_and_order_sensitive():
    assert stable_id("project", "file.py") == stable_id("project", "file.py")
    assert stable_id("project", "file.py") != stable_id("file.py", "project")


def test_round_trip_snapshot_and_integrity_check(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src/main.py").write_text("import os\n", encoding="utf-8")
    (tmp_path / "src/util.py").write_text("VALUE = 1\n", encoding="utf-8")
    store = IndexGraphStore(tmp_path)
    first = _node(tmp_path, "src/main.py")
    second = _node(tmp_path, "src/util.py")
    edge = _edge(from_id=first.id, to_id=second.id)

    store.replace_snapshot(_manifest(tmp_path), [first, second], [edge])
    manifest, nodes, edges = store.load_snapshot()

    assert manifest is not None
    assert manifest.status is IndexStatus.READY
    assert {node.path for node in nodes} == {"src/main.py", "src/util.py"}
    assert len(edges) == 1
    assert edges[0].relation == "imports"
    assert store.integrity_check() == "ok"
    assert store.db_path.is_relative_to(tmp_path.resolve())


def test_empty_store_returns_empty_snapshot(tmp_path):
    manifest, nodes, edges = IndexGraphStore(tmp_path).load_snapshot()
    assert manifest is None
    assert nodes == []
    assert edges == []


def test_rejects_storage_directory_outside_project(tmp_path):
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    with pytest.raises(ValueError, match="inside the project root"):
        IndexGraphStore(tmp_path, outside)


def test_rejects_manifest_for_another_project_root(tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    store = IndexGraphStore(tmp_path)
    with pytest.raises(ValueError, match="canonical_root"):
        store.replace_snapshot(_manifest(other), [], [])


@pytest.mark.parametrize("path", [
    "../outside.py",
    "/etc/passwd",
    "src\\\\main.py",
    "src/../outside.py",
    ".",
])
def test_rejects_noncanonical_or_escaping_node_paths(tmp_path, path):
    with pytest.raises(ValueError):
        from agent.indexgraph import validate_node
        validate_node(_node(tmp_path, path), tmp_path.resolve())


def test_rejects_edge_with_missing_endpoint(tmp_path):
    node = _node(tmp_path)
    edge = _edge(from_id=node.id, to_id="missing")
    with pytest.raises(ValueError, match="endpoints"):
        IndexGraphStore(tmp_path).replace_snapshot(_manifest(tmp_path), [node], [edge])


def test_rejects_duplicate_node_ids(tmp_path):
    one = _node(tmp_path, "src/a.py", node_id="duplicate")
    two = _node(tmp_path, "src/b.py", node_id="duplicate")
    with pytest.raises(ValueError, match="duplicate node"):
        IndexGraphStore(tmp_path).replace_snapshot(_manifest(tmp_path), [one, two], [])


def test_invalid_candidate_does_not_replace_last_good_snapshot(tmp_path):
    store = IndexGraphStore(tmp_path)
    good = _node(tmp_path, "src/good.py")
    store.replace_snapshot(_manifest(tmp_path), [good], [])

    invalid = _node(tmp_path, "../escape.py")
    with pytest.raises(ValueError):
        store.replace_snapshot(_manifest(tmp_path), [invalid], [])

    manifest, nodes, edges = store.load_snapshot()
    assert manifest is not None
    assert [node.id for node in nodes] == [good.id]
    assert edges == []


def test_rejects_symlink_path_escaping_project(tmp_path):
    outside = tmp_path.parent / f"{tmp_path.name}-outside-file.py"
    outside.write_text("SECRET = True\n", encoding="utf-8")
    link = tmp_path / "external.py"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is not available on this host")
    from agent.indexgraph import validate_node
    with pytest.raises(ValueError, match="outside"):
        validate_node(_node(tmp_path, "external.py"), tmp_path.resolve())


def test_rejects_unbounded_attributes(tmp_path):
    node = GraphNode(
        id="large",
        kind="file",
        label="main.py",
        path="main.py",
        source_fingerprint="fp",
        extractor_id="test",
        extractor_version="1",
        attributes={"payload": "x" * 20_000},
    )
    from agent.indexgraph import validate_node
    with pytest.raises(ValueError, match="exceeds"):
        validate_node(node, tmp_path.resolve())


def test_rejects_invalid_coverage_counts(tmp_path):
    manifest = IndexManifest(
        project_id=project_id_for(tmp_path),
        canonical_root=str(tmp_path.resolve()),
        source_revision=None,
        provider_id="test",
        provider_version="1",
        status=IndexStatus.PARTIAL,
        discovered_files=1,
        indexed_files=2,
    )
    with pytest.raises(ValueError, match="cannot exceed"):
        IndexGraphStore(tmp_path).replace_snapshot(manifest, [], [])
