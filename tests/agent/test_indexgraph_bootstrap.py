"""Tests for deterministic, model-free IndexGraph bootstrap."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent.indexgraph import IndexGraphStore, IndexStatus
from agent.indexgraph_bootstrap import BootstrapPolicy, build_index


def test_bootstrap_is_deterministic_and_emits_confirmed_local_imports(tmp_path: Path) -> None:
    package = tmp_path / "src" / "pkg"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "main.py").write_text("from .util import value\nfrom . import util\n", encoding="utf-8")
    (package / "util.py").write_text("value = 42\n", encoding="utf-8")

    first = build_index(tmp_path)
    second = build_index(tmp_path)

    assert first.manifest.project_id == second.manifest.project_id
    assert first.indexed_paths == second.indexed_paths
    assert {node.id for node in first.nodes} == {node.id for node in second.nodes}
    assert {(edge.from_id, edge.relation, edge.to_id) for edge in first.edges} == {
        (edge.from_id, edge.relation, edge.to_id) for edge in second.edges
    }
    main = next(node for node in first.nodes if node.path == "src/pkg/main.py")
    util = next(node for node in first.nodes if node.path == "src/pkg/util.py")
    imports = [
        edge for edge in first.edges
        if edge.from_id == main.id and edge.to_id == util.id and edge.relation == "imports"
    ]
    assert len(imports) == 2
    assert len({edge.id for edge in imports}) == 2
    assert all(edge.confidence.value == "confirmed" for edge in first.edges)


def test_bootstrap_extracts_manifest_dependencies_without_model_calls(tmp_path: Path) -> None:
    manifest_path = tmp_path / "package.json"
    manifest_path.write_text(json.dumps({
        "name": "sample",
        "dependencies": {"fastify": "^5.0.0"},
        "devDependencies": {"vitest": "^3.0.0"},
    }), encoding="utf-8")

    report = build_index(tmp_path)
    packages = [node for node in report.nodes if node.kind == "package"]
    assert {(node.label, node.attributes["specifier"]) for node in packages} == {
        ("fastify", "^5.0.0"), ("vitest", "^3.0.0"),
    }
    manifest_node = next(node for node in report.nodes if node.path == "package.json")
    assert all(
        edge.from_id == manifest_node.id and edge.relation == "declares_dependency"
        for edge in report.edges if edge.relation == "declares_dependency"
    )


def test_bootstrap_excludes_secret_files_and_generated_directories(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('safe')\n", encoding="utf-8")
    (tmp_path / ".env").write_text("TOKEN=must-not-be-read\n", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "ignored.py").write_text("SECRET = True\n", encoding="utf-8")

    report = build_index(tmp_path)

    assert report.indexed_paths == ("src/main.py",)
    assert all("TOKEN" not in str(node.attributes) for node in report.nodes)
    assert "node_modules/ignored.py" not in report.indexed_paths


def test_bootstrap_marks_oversized_files_partial(tmp_path: Path) -> None:
    (tmp_path / "large.py").write_text("x" * 128, encoding="utf-8")

    report = build_index(tmp_path, BootstrapPolicy(max_file_bytes=64))

    assert report.manifest.status is IndexStatus.PARTIAL
    assert report.manifest.unsupported_files == 1
    assert "large.py" not in report.indexed_paths


def test_bootstrap_does_not_follow_symlinks_outside_project(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside.py"
    outside.write_text("SECRET = True\n", encoding="utf-8")
    link = tmp_path / "linked.py"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is not available on this host")

    report = build_index(tmp_path)

    assert "linked.py" not in report.indexed_paths
    assert report.manifest.excluded_files >= 1


def test_snapshot_is_accepted_by_transactional_store(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('ok')\n", encoding="utf-8")
    report = build_index(tmp_path)

    store = IndexGraphStore(tmp_path)
    store.replace_snapshot(report.manifest, report.nodes, report.edges)
    manifest, nodes, edges = store.load_snapshot()

    assert manifest == report.manifest
    assert len(nodes) == len(report.nodes)
    assert len(edges) == len(report.edges)
    assert store.integrity_check() == "ok"
