"""Tests for IndexGraph freshness, extraction reuse, and transactional deltas."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from agent.indexgraph import IndexGraphStore
from agent.indexgraph_incremental import refresh_index


def test_initial_refresh_indexes_all_files_and_persists_snapshot(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("value = 1\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("value = 2\n", encoding="utf-8")
    store = IndexGraphStore(tmp_path)

    report = refresh_index(tmp_path, store=store)
    manifest, nodes, _edges = store.load_snapshot()

    assert set(report.changed_paths) == {"a.py", "b.py"}
    assert report.deleted_paths == ()
    assert report.unchanged_paths == ()
    assert set(report.parsed_paths) == {"a.py", "b.py"}
    assert report.full_extraction_scan is True
    assert report.full_scan is True
    assert manifest is not None
    assert {node.path for node in nodes if node.kind == "file"} == {"a.py", "b.py"}
    assert store.integrity_check() == "ok"


def test_no_source_changes_reuses_extraction_and_writes_no_graph_rows(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("value = 1\n", encoding="utf-8")
    store = IndexGraphStore(tmp_path)
    refresh_index(tmp_path, store=store)

    report = refresh_index(tmp_path, store=store)

    assert report.changed_paths == ()
    assert report.deleted_paths == ()
    assert report.unchanged_paths == ("a.py",)
    assert report.parsed_paths == ()
    assert report.full_extraction_scan is False
    assert report.inserted_or_updated_nodes == 0
    assert report.deleted_nodes == 0
    assert report.inserted_or_updated_edges == 0
    assert report.deleted_edges == 0


def test_same_path_set_parses_only_the_changed_file(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("value = 1\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("value = 2\n", encoding="utf-8")
    store = IndexGraphStore(tmp_path)
    refresh_index(tmp_path, store=store)

    (tmp_path / "b.py").write_text("value = 3\n", encoding="utf-8")
    report = refresh_index(tmp_path, store=store)

    assert report.changed_paths == ("b.py",)
    assert report.parsed_paths == ("b.py",)
    assert report.full_extraction_scan is False
    assert report.unchanged_paths == ("a.py",)


def test_path_set_change_reextracts_importers_and_removes_stale_edges(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    importer = source / "a.py"
    dependency = source / "b.py"
    importer.write_text("from .b import value\n", encoding="utf-8")
    dependency.write_text("value = 42\n", encoding="utf-8")
    store = IndexGraphStore(tmp_path)
    refresh_index(tmp_path, store=store)
    _manifest, nodes, edges = store.load_snapshot()
    importer_node = next(node for node in nodes if node.path == "src/a.py")
    dependency_node = next(node for node in nodes if node.path == "src/b.py")
    assert any(
        edge.relation == "imports" and edge.from_id == importer_node.id
        and edge.to_id == dependency_node.id for edge in edges
    )

    dependency.unlink()
    report = refresh_index(tmp_path, store=store)
    _manifest, nodes, edges = store.load_snapshot()
    importer_node = next(node for node in nodes if node.path == "src/a.py")

    assert report.deleted_paths == ("src/b.py",)
    assert "src/a.py" in report.parsed_paths
    assert report.full_extraction_scan is True
    assert not any(edge.relation == "imports" and edge.from_id == importer_node.id for edge in edges)
    assert not any(node.path == "src/b.py" for node in nodes)
    assert store.integrity_check() == "ok"


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
    assert "src/changed.py" in report.parsed_paths
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
    with pytest.raises(ValueError, match="duplicate edge id"):
        store.apply_snapshot_delta(manifest, nodes, [*edges, edges[0]])

    assert store.load_snapshot() == before
    assert store.integrity_check() == "ok"


def test_sqlite_write_failure_rolls_back_entire_delta(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("value = 1\n", encoding="utf-8")
    store = IndexGraphStore(tmp_path)
    refresh_index(tmp_path, store=store)
    before = store.load_snapshot()
    with sqlite3.connect(store.db_path) as connection:
        connection.execute("""
            CREATE TRIGGER fail_selected_node_insert
            BEFORE INSERT ON nodes
            WHEN NEW.path = 'fail.py'
            BEGIN SELECT RAISE(ABORT, 'injected write failure'); END;
        """)

    (tmp_path / "fail.py").write_text("value = 2\n", encoding="utf-8")
    with pytest.raises(sqlite3.IntegrityError, match="injected write failure"):
        refresh_index(tmp_path, store=store)

    assert store.load_snapshot() == before
    assert store.integrity_check() == "ok"
