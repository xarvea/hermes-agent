"""Project-scoped IndexGraph schema and transactional SQLite storage.

This module deliberately does not crawl files or infer dependencies. It provides
validated, bounded persistence for a future deterministic index provider.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

SCHEMA_VERSION = 1
DEFAULT_INDEX_DIR = Path(".engineering-agent") / "indexgraph"
MAX_LABEL_CHARS = 512
MAX_JSON_FIELD_BYTES = 16_384
MAX_PROVENANCE_BYTES = 4_096
MAX_ERRORS = 100
MAX_ERROR_CHARS = 512

NODE_KINDS = frozenset({
    "project", "directory", "file", "package", "manifest", "symbol",
    "test", "api_route", "config",
})
EDGE_RELATIONS = frozenset({
    "contains", "imports", "declares_dependency", "tests", "configures", "references",
})


class IndexStatus(str, Enum):
    NOT_INDEXED = "NOT_INDEXED"
    DISCOVERING = "DISCOVERING"
    BUILDING = "BUILDING"
    READY = "READY"
    PARTIAL = "PARTIAL"
    STALE = "STALE"
    FAILED = "FAILED"


class Confidence(str, Enum):
    CONFIRMED = "confirmed"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


def utc_now() -> str:
    """Return an ISO-8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def stable_id(*parts: str) -> str:
    """Return a deterministic, non-reversible identifier for structured identity parts."""
    payload = json.dumps(parts, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def project_id_for(root: str | Path, repository_identity: str = "") -> str:
    """Derive a project namespace from its canonical root and optional repository identity.

    Callers should pass a non-secret repository identity (for example, a normalized
    origin URL with embedded credentials removed). The root remains part of the
    namespace so unrelated local checkouts do not share an index by accident.
    """
    canonical_root = Path(root).expanduser().resolve(strict=True)
    if not canonical_root.is_dir():
        raise ValueError("project root must be a directory")
    return stable_id(str(canonical_root), repository_identity)


@dataclass(frozen=True)
class IndexManifest:
    project_id: str
    canonical_root: str
    source_revision: str | None
    provider_id: str
    provider_version: str
    status: IndexStatus
    discovered_files: int = 0
    indexed_files: int = 0
    excluded_files: int = 0
    unsupported_files: int = 0
    failed_files: int = 0
    config_fingerprint: str = ""
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    last_success_at: str | None = None
    errors: tuple[str, ...] = ()

    def to_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["status"] = self.status.value
        record["errors"] = list(self.errors[:MAX_ERRORS])
        return record

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "IndexManifest":
        values = dict(record)
        values["status"] = IndexStatus(values["status"])
        values["errors"] = tuple(values.get("errors", ()))
        return cls(**values)


@dataclass(frozen=True)
class GraphNode:
    id: str
    kind: str
    label: str
    path: str
    source_fingerprint: str
    extractor_id: str
    extractor_version: str
    confidence: Confidence = Confidence.CONFIRMED
    start_line: int | None = None
    end_line: int | None = None
    symbol: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["confidence"] = self.confidence.value
        return record

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "GraphNode":
        values = dict(record)
        values["confidence"] = Confidence(values["confidence"])
        return cls(**values)


@dataclass(frozen=True)
class GraphEdge:
    id: str
    from_id: str
    relation: str
    to_id: str
    source_path: str
    source_fingerprint: str
    extractor_id: str
    extractor_version: str
    confidence: Confidence = Confidence.CONFIRMED
    start_line: int | None = None
    end_line: int | None = None

    def to_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["confidence"] = self.confidence.value
        return record

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "GraphEdge":
        values = dict(record)
        values["confidence"] = Confidence(values["confidence"])
        return cls(**values)


def _bounded_json(value: Any, *, max_bytes: int, field_name: str) -> str:
    try:
        encoded = json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be JSON-serializable") from exc
    if len(encoded.encode("utf-8")) > max_bytes:
        raise ValueError(f"{field_name} exceeds {max_bytes} bytes")
    return encoded


def _relative_path(root: Path, value: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or not value:
        if allow_empty and value == "":
            return ""
        raise ValueError("project-relative path must be a non-empty string")
    if "\\" in value or value.startswith("/"):
        raise ValueError("path must be a relative POSIX path")
    parsed = PurePosixPath(value)
    if parsed.as_posix() != value or parsed.is_absolute() or not parsed.parts or any(part in {"", ".", ".."} for part in parsed.parts):
        raise ValueError("path traversal or non-canonical path is not allowed")
    candidate = (root / Path(*parsed.parts)).resolve(strict=False)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("path resolves outside the canonical project root") from exc
    return parsed.as_posix()


def validate_manifest(manifest: IndexManifest, root: Path) -> None:
    if manifest.canonical_root != str(root):
        raise ValueError("manifest canonical_root does not match the store root")
    if not isinstance(manifest.status, IndexStatus):
        raise ValueError("manifest status must be an IndexStatus value")
    for name, value in (
        ("project_id", manifest.project_id),
        ("provider_id", manifest.provider_id),
        ("provider_version", manifest.provider_version),
    ):
        if not isinstance(value, str) or not value.strip() or len(value) > MAX_LABEL_CHARS:
            raise ValueError(f"{name} must be a non-empty bounded string")
    if len(manifest.errors) > MAX_ERRORS:
        raise ValueError(f"errors may contain at most {MAX_ERRORS} entries")
    for error in manifest.errors:
        if not isinstance(error, str) or len(error) > MAX_ERROR_CHARS:
            raise ValueError("each manifest error must be a bounded string")
    counts = (
        manifest.discovered_files, manifest.indexed_files, manifest.excluded_files,
        manifest.unsupported_files, manifest.failed_files,
    )
    if any(not isinstance(count, int) or isinstance(count, bool) or count < 0 for count in counts):
        raise ValueError("coverage counts must be non-negative integers")
    if manifest.indexed_files > manifest.discovered_files:
        raise ValueError("indexed_files cannot exceed discovered_files")
    _bounded_json(manifest.to_record(), max_bytes=MAX_JSON_FIELD_BYTES * 2, field_name="manifest")


def validate_node(node: GraphNode, root: Path) -> None:
    for name, value in (
        ("id", node.id), ("kind", node.kind), ("label", node.label),
        ("extractor_id", node.extractor_id), ("extractor_version", node.extractor_version),
    ):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"node {name} must be a non-empty string")
    if node.kind not in NODE_KINDS:
        raise ValueError(f"unsupported node kind: {node.kind}")
    if not isinstance(node.confidence, Confidence):
        raise ValueError("node confidence must be a Confidence value")
    if len(node.label) > MAX_LABEL_CHARS:
        raise ValueError("node label exceeds the configured limit")
    _relative_path(root, node.path, allow_empty=(node.kind == "project"))
    if not isinstance(node.source_fingerprint, str) or len(node.source_fingerprint) > MAX_LABEL_CHARS:
        raise ValueError("node source_fingerprint must be a bounded string")
    if node.start_line is not None and (not isinstance(node.start_line, int) or node.start_line < 1):
        raise ValueError("start_line must be a positive integer")
    if node.end_line is not None and (not isinstance(node.end_line, int) or node.end_line < 1):
        raise ValueError("end_line must be a positive integer")
    if node.start_line and node.end_line and node.end_line < node.start_line:
        raise ValueError("end_line cannot precede start_line")
    _bounded_json(node.attributes, max_bytes=MAX_JSON_FIELD_BYTES, field_name="node attributes")


def validate_edge(edge: GraphEdge, root: Path, node_ids: set[str]) -> None:
    for name, value in (
        ("id", edge.id), ("from_id", edge.from_id), ("to_id", edge.to_id),
        ("relation", edge.relation), ("extractor_id", edge.extractor_id),
        ("extractor_version", edge.extractor_version),
    ):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"edge {name} must be a non-empty string")
    if edge.relation not in EDGE_RELATIONS:
        raise ValueError(f"unsupported edge relation: {edge.relation}")
    if not isinstance(edge.confidence, Confidence):
        raise ValueError("edge confidence must be a Confidence value")
    if edge.from_id not in node_ids or edge.to_id not in node_ids:
        raise ValueError("edge endpoints must reference nodes in the same snapshot")
    _relative_path(root, edge.source_path)
    if not isinstance(edge.source_fingerprint, str) or len(edge.source_fingerprint) > MAX_LABEL_CHARS:
        raise ValueError("edge source_fingerprint must be a bounded string")
    if edge.start_line is not None and (not isinstance(edge.start_line, int) or edge.start_line < 1):
        raise ValueError("edge start_line must be a positive integer")
    if edge.end_line is not None and (not isinstance(edge.end_line, int) or edge.end_line < 1):
        raise ValueError("edge end_line must be a positive integer")
    if edge.start_line and edge.end_line and edge.end_line < edge.start_line:
        raise ValueError("edge end_line cannot precede start_line")


class IndexGraphStore:
    """Project-local SQLite store with validated, transactional snapshot replacement."""

    def __init__(self, project_root: str | Path, index_dir: str | Path | None = None):
        root = Path(project_root).expanduser().resolve(strict=True)
        if not root.is_dir():
            raise ValueError("project_root must be a directory")
        raw_dir = Path(index_dir) if index_dir is not None else root / DEFAULT_INDEX_DIR
        if not raw_dir.is_absolute():
            raw_dir = root / raw_dir
        resolved_dir = raw_dir.resolve(strict=False)
        try:
            resolved_dir.relative_to(root)
        except ValueError as exc:
            raise ValueError("IndexGraph storage must remain inside the project root") from exc
        self.root = root
        self.index_dir = resolved_dir
        self.db_path = resolved_dir / "index.sqlite3"
        # Resolve the final path too: an existing database symlink must not escape the root.
        resolved_db = self.db_path.resolve(strict=False)
        try:
            resolved_db.relative_to(root)
        except ValueError as exc:
            raise ValueError("IndexGraph database path resolves outside the project root") from exc
        self.db_path = resolved_db

    def _connect(self) -> sqlite3.Connection:
        self.index_dir.mkdir(parents=True, exist_ok=True)
        # Recheck after mkdir to narrow symlink/path races before opening the database.
        actual_dir = self.index_dir.resolve(strict=True)
        try:
            actual_dir.relative_to(self.root)
        except ValueError as exc:
            raise ValueError("IndexGraph storage escaped the project root") from exc
        actual_db = self.db_path.resolve(strict=False)
        try:
            actual_db.relative_to(self.root)
        except ValueError as exc:
            raise ValueError("IndexGraph database escaped the project root") from exc
        connection = sqlite3.connect(str(actual_db), timeout=10.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 10000")
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS manifest (
                singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                path TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_indexgraph_nodes_path ON nodes(path);
            CREATE INDEX IF NOT EXISTS idx_indexgraph_nodes_kind ON nodes(kind);
            CREATE TABLE IF NOT EXISTS edges (
                id TEXT PRIMARY KEY,
                from_id TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
                to_id TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
                relation TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_indexgraph_edges_from ON edges(from_id);
            CREATE INDEX IF NOT EXISTS idx_indexgraph_edges_to ON edges(to_id);
            CREATE INDEX IF NOT EXISTS idx_indexgraph_edges_relation ON edges(relation);
            PRAGMA user_version = 1;
            """
        )
        return connection

    @contextmanager
    def _connection(self):
        """Open a short-lived connection and always commit/rollback and close it."""
        connection = self._connect()
        try:
            yield connection
            if connection.in_transaction:
                connection.commit()
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def replace_snapshot(
        self,
        manifest: IndexManifest,
        nodes: Iterable[GraphNode],
        edges: Iterable[GraphEdge],
    ) -> None:
        """Validate and atomically replace the complete snapshot.

        Validation happens before deleting old rows. SQLite transaction rollback
        preserves the previous snapshot if any write fails.
        """
        if not isinstance(manifest, IndexManifest):
            raise TypeError("manifest must be an IndexManifest")
        validate_manifest(manifest, self.root)
        node_list = list(nodes)
        edge_list = list(edges)
        node_ids: set[str] = set()
        for node in node_list:
            validate_node(node, self.root)
            if node.id in node_ids:
                raise ValueError(f"duplicate node id: {node.id}")
            node_ids.add(node.id)
        edge_ids: set[str] = set()
        for edge in edge_list:
            validate_edge(edge, self.root, node_ids)
            if edge.id in edge_ids:
                raise ValueError(f"duplicate edge id: {edge.id}")
            edge_ids.add(edge.id)
        manifest_json = _bounded_json(
            manifest.to_record(), max_bytes=MAX_JSON_FIELD_BYTES * 2, field_name="manifest",
        )
        node_rows = [
            (node.id, node.kind, node.path, _bounded_json(node.to_record(),
             max_bytes=MAX_JSON_FIELD_BYTES * 2, field_name="node"))
            for node in node_list
        ]
        edge_rows = [
            (edge.id, edge.from_id, edge.to_id, edge.relation,
             _bounded_json(edge.to_record(), max_bytes=MAX_PROVENANCE_BYTES * 4, field_name="edge"))
            for edge in edge_list
        ]
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM edges")
            connection.execute("DELETE FROM nodes")
            connection.execute("DELETE FROM manifest")
            connection.executemany(
                "INSERT INTO nodes (id, kind, path, payload) VALUES (?, ?, ?, ?)", node_rows,
            )
            connection.executemany(
                "INSERT INTO edges (id, from_id, to_id, relation, payload) VALUES (?, ?, ?, ?, ?)",
                edge_rows,
            )
            connection.execute("INSERT INTO manifest (singleton, payload) VALUES (1, ?)", (manifest_json,))

    def load_snapshot(self) -> tuple[IndexManifest | None, list[GraphNode], list[GraphEdge]]:
        """Load the current validated-schema snapshot; returns an empty result before first build."""
        with self._connection() as connection:
            row = connection.execute("SELECT payload FROM manifest WHERE singleton = 1").fetchone()
            manifest = IndexManifest.from_record(json.loads(row["payload"])) if row else None
            nodes = [
                GraphNode.from_record(json.loads(row["payload"]))
                for row in connection.execute("SELECT payload FROM nodes ORDER BY id")
            ]
            edges = [
                GraphEdge.from_record(json.loads(row["payload"]))
                for row in connection.execute("SELECT payload FROM edges ORDER BY id")
            ]
        if manifest is not None:
            validate_manifest(manifest, self.root)
            node_ids: set[str] = set()
            for node in nodes:
                validate_node(node, self.root)
                if node.id in node_ids:
                    raise ValueError("stored snapshot contains duplicate node ids")
                node_ids.add(node.id)
            edge_ids: set[str] = set()
            for edge in edges:
                validate_edge(edge, self.root, node_ids)
                if edge.id in edge_ids:
                    raise ValueError("stored snapshot contains duplicate edge ids")
                edge_ids.add(edge.id)
        elif nodes or edges:
            raise ValueError("stored graph rows exist without a manifest")
        return manifest, nodes, edges

    def integrity_check(self) -> str:
        """Run SQLite's built-in integrity check and return its result."""
        with self._connection() as connection:
            row = connection.execute("PRAGMA integrity_check").fetchone()
        return str(row[0]) if row else "unknown"
