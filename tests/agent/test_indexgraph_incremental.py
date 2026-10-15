"""Tests for IndexGraph freshness and delta persistence."""
from __future__ import annotations

from pathlib import Path

from agent.indexgraph import IndexGraphStore
from agent.indexgraph_incremental import refresh_index


def test_initial_refresh_indexes_all_files_and_persists_snapshot(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("value = 1\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("value = 2\n", encoding="utf-8")
    store = IndexGraphStore(tmp_path)

    report = refresh_index(tmp_path, store=store)
    manifest, nodes, edges = store.load_snapshot()

    assert set(report.changed_paths) == {"a.py", "b.py"}
    assert report.deleted_paths == ()
    assert report.unchanged_paths == ()
    assert report.full_scan is True
    assert manifest is not None
    assert {node.path for node in nodes if node.kind == "file"} == {"a.py", "b.py"}
    assert store.integrity_check() == "ok"


def test_no_source_changes_produce_no_graph_row_writes(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("value = 1\n", encoding="utf-8")
    store = IndexGraphStore(tmp_path)
    refresh_index(tmp_path, store=store)

    report = refresh_index(tmp_path, store=store)

    assert report.changed_paths == ()
    assert report.deleted_paths == ()
    assert report.unchanged_paths == ("a.py",)
    assert report.inserted_or_updated_nodes == 0
    assert report.deleted_nodes == 0
    assert report.inserted_or_updated_edges == 0
    assert report.deleted_edges == 0


def test_refresh_updates_changed_file_and_deletes_removed_file(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    changed = source / "changed.py"
    removed = source / "removed.py"
    changed.write_text("value = 1\n", encoding="utf-8")
    removed.write_text("value = 2\n", encoding="utf-8")
    store = IndexGraphStore(tmp_path)
    refresh_index(tmp_path, store=store)

    changed.write_text("value = 3\n", encoding="utf-8")
    removed.unlink()
    report = refresh_index(tmp_path, store=store)
    manifest, nodes, _edges = store.load_snapshot()

    assert report.changed_paths == ("src/changed.py",)
    assert report.deleted_paths == ("src/removed.py",)
    assert report.unchanged_paths == ()
    assert report.inserted_or_updated_nodes >= 1
    assert report.deleted_nodes >= 1
    assert manifest is not None
    assert not any(node.path == "src/removed.py" for node in nodes)
    changed_node = next(node for node in nodes if node.path == "src/changed.py")
    assert changed_node.source_fingerprint.startswith("sha256:")
    assert store.integrity_check() == "ok"


def test_failed_delta_validation_preserves_previous_snapshot(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("value = 1\n", encoding="utf-8")
    store = IndexGraphStore(tmp_path)
    refresh_index(tmp_path, store=store)
    before = store.load_snapshot()

    manifest, nodes, edges = before
    assert manifest is not None
    try:
        store.apply_snapshot_delta(manifest, nodes, [*edges, edges[0]])
    except ValueError as exc:
        assert "duplicate edge id" in str(exc)
    else:
        raise AssertionError("duplicate edge id should be rejected")

    after = store.load_snapshot()
    assert after == before
    assert store.integrity_check() == "ok"
