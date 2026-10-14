#!/usr/bin/env python3
"""Small, durable task ledger for the Autonomous Engineering Agent skill.

This module intentionally uses only the Python standard library. It records task
state and verification evidence; it does not execute commands or grant permissions.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import json
import sqlite3
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

SCHEMA_VERSION = 1
STATUSES = {"PENDING", "IN_PROGRESS", "BLOCKED", "COMPLETED", "FAILED"}
TRANSITIONS = {
    "PENDING": {"IN_PROGRESS", "BLOCKED", "FAILED"},
    "IN_PROGRESS": {"PENDING", "BLOCKED", "COMPLETED", "FAILED"},
    "BLOCKED": {"PENDING", "IN_PROGRESS", "FAILED"},
    "FAILED": {"PENDING"},
    "COMPLETED": set(),
}


class TaskLedgerError(Exception):
    """Expected, user-correctable task ledger error."""


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 10000")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def _initialize(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS ledger_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL CHECK (status IN
                ('PENDING','IN_PROGRESS','BLOCKED','COMPLETED','FAILED')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            evidence TEXT NOT NULL DEFAULT '',
            blocked_reason TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS task_dependencies (
            task_id TEXT NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
            depends_on TEXT NOT NULL REFERENCES tasks(task_id) ON DELETE RESTRICT,
            PRIMARY KEY (task_id, depends_on),
            CHECK (task_id <> depends_on)
        );
        CREATE TABLE IF NOT EXISTS task_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL REFERENCES tasks(task_id),
            event_type TEXT NOT NULL,
            from_status TEXT,
            to_status TEXT,
            details TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
        CREATE INDEX IF NOT EXISTS idx_task_events_task ON task_events(task_id, event_id);
        """
    )
    existing = conn.execute(
        "SELECT value FROM ledger_meta WHERE key = 'schema_version'"
    ).fetchone()
    if existing is None:
        conn.execute(
            "INSERT INTO ledger_meta(key, value) VALUES ('schema_version', ?)",
            (str(SCHEMA_VERSION),),
        )
    elif int(existing["value"]) != SCHEMA_VERSION:
        raise TaskLedgerError(
            f"Unsupported ledger schema {existing['value']}; expected {SCHEMA_VERSION}. "
            "Back up the database and run a supported migration."
        )


def _validate_task_id(task_id: str) -> str:
    value = task_id.strip()
    if not value or len(value) > 80:
        raise TaskLedgerError("Task ID must contain 1–80 non-whitespace characters.")
    return value


def _task(conn: sqlite3.Connection, task_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
    if row is None:
        raise TaskLedgerError(f"Task not found: {task_id}")
    return row


def _record_event(
    conn: sqlite3.Connection,
    task_id: str,
    event_type: str,
    from_status: str | None,
    to_status: str | None,
    details: str,
) -> None:
    conn.execute(
        """INSERT INTO task_events
           (task_id, event_type, from_status, to_status, details, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (task_id, event_type, from_status, to_status, details, _now()),
    )


def _would_create_cycle(
    conn: sqlite3.Connection, task_id: str, dependency_ids: Iterable[str]
) -> bool:
    graph: dict[str, set[str]] = {}
    for row in conn.execute("SELECT task_id, depends_on FROM task_dependencies"):
        graph.setdefault(row["task_id"], set()).add(row["depends_on"])
    graph[task_id] = set(dependency_ids)
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for parent in graph.get(node, set()):
            if visit(parent):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in graph if node not in visited)


def create_task(
    db_path: Path,
    title: str,
    description: str = "",
    dependencies: Iterable[str] = (),
) -> dict:
    title = title.strip()
    if not title:
        raise TaskLedgerError("Task title cannot be empty.")
    if len(title) > 240:
        raise TaskLedgerError("Task title cannot exceed 240 characters.")
    dependency_ids = sorted({_validate_task_id(item) for item in dependencies})
    task_id = uuid.uuid4().hex[:12]
    now = _now()
    with closing(_connect(db_path)) as conn, conn:
        _initialize(conn)
        conn.execute("BEGIN IMMEDIATE")
        try:
            for dependency_id in dependency_ids:
                _task(conn, dependency_id)
            if _would_create_cycle(conn, task_id, dependency_ids):
                raise TaskLedgerError("Dependencies would create a cycle.")
            conn.execute(
                """INSERT INTO tasks
                   (task_id, title, description, status, created_at, updated_at)
                   VALUES (?, ?, ?, 'PENDING', ?, ?)""",
                (task_id, title, description.strip(), now, now),
            )
            for dependency_id in dependency_ids:
                conn.execute(
                    "INSERT INTO task_dependencies(task_id, depends_on) VALUES (?, ?)",
                    (task_id, dependency_id),
                )
            _record_event(conn, task_id, "CREATED", None, "PENDING", title)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return get_task(db_path, task_id)


def transition_task(
    db_path: Path,
    task_id: str,
    target: str,
    details: str = "",
) -> dict:
    task_id = _validate_task_id(task_id)
    target = target.upper()
    if target not in STATUSES:
        raise TaskLedgerError(f"Unknown status: {target}")
    if target == "COMPLETED" and not details.strip():
        raise TaskLedgerError("Completion requires verification evidence (--evidence).")
    if target == "BLOCKED" and not details.strip():
        raise TaskLedgerError("Blocking a task requires a reason (--reason).")

    with closing(_connect(db_path)) as conn, conn:
        _initialize(conn)
        conn.execute("BEGIN IMMEDIATE")
        try:
            current = _task(conn, task_id)
            old_status = current["status"]
            if target not in TRANSITIONS[old_status]:
                raise TaskLedgerError(f"Invalid transition: {old_status} -> {target}")
            if target == "IN_PROGRESS":
                unfinished = conn.execute(
                    """SELECT d.depends_on, t.status FROM task_dependencies d
                       JOIN tasks t ON t.task_id = d.depends_on
                       WHERE d.task_id = ? AND t.status <> 'COMPLETED'""",
                    (task_id,),
                ).fetchall()
                if unfinished:
                    blockers = ", ".join(
                        f"{row['depends_on']} ({row['status']})" for row in unfinished
                    )
                    raise TaskLedgerError(f"Dependencies are not complete: {blockers}")
            now = _now()
            evidence = details if target == "COMPLETED" else current["evidence"]
            blocked_reason = details if target == "BLOCKED" else ""
            conn.execute(
                """UPDATE tasks SET status = ?, updated_at = ?, evidence = ?,
                   blocked_reason = ? WHERE task_id = ?""",
                (target, now, evidence, blocked_reason, task_id),
            )
            _record_event(conn, task_id, "STATUS_CHANGED", old_status, target, details)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return get_task(db_path, task_id)


def get_task(db_path: Path, task_id: str) -> dict:
    with closing(_connect(db_path)) as conn, conn:
        _initialize(conn)
        row = _task(conn, _validate_task_id(task_id))
        result = dict(row)
        result["dependencies"] = [
            item["depends_on"]
            for item in conn.execute(
                "SELECT depends_on FROM task_dependencies WHERE task_id = ? ORDER BY depends_on",
                (task_id,),
            )
        ]
        result["events"] = [
            dict(item)
            for item in conn.execute(
                "SELECT event_id, event_type, from_status, to_status, details, created_at "
                "FROM task_events WHERE task_id = ? ORDER BY event_id",
                (task_id,),
            )
        ]
        return result


def list_tasks(db_path: Path) -> list[dict]:
    with closing(_connect(db_path)) as conn, conn:
        _initialize(conn)
        rows = conn.execute(
            """SELECT task_id, title, description, status, created_at, updated_at,
                      evidence, blocked_reason
               FROM tasks ORDER BY created_at, task_id"""
        ).fetchall()
        return [dict(row) for row in rows]


def _db_path(project_root: str, state_file: str | None) -> Path:
    root = Path(project_root).expanduser().resolve()
    if not root.is_dir():
        raise TaskLedgerError(f"Project root is not a directory: {root}")
    candidate = Path(state_file).expanduser() if state_file else root / ".engineering-agent" / "state.sqlite3"
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve()
    if candidate != root and root not in candidate.parents:
        raise TaskLedgerError("State database must remain inside the project root.")
    return candidate


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=".", help="Project directory (default: current directory).")
    parser.add_argument("--state-file", help="Optional database path, constrained to project root.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="Initialize the task ledger.")
    sub.add_parser("list", help="List all tasks.")
    create = sub.add_parser("create", help="Create a task.")
    create.add_argument("--title", required=True)
    create.add_argument("--description", default="")
    create.add_argument("--depends-on", action="append", default=[], dest="dependencies")
    show = sub.add_parser("show", help="Show task, dependencies and event history.")
    show.add_argument("task_id")
    for name in ("start", "unblock", "complete", "block", "fail"):
        command = sub.add_parser(name, help=f"Move a task to {name}.")
        command.add_argument("task_id")
        if target == "COMPLETED":
            command.add_argument("--evidence", required=True, help="Test or verification evidence.")
        elif target == "BLOCKED":
            command.add_argument("--reason", required=True)
        else:
            command.add_argument("--details", default="")
    return parser


def _initialize_ledger(db_path: Path) -> dict:
    with closing(_connect(db_path)) as conn, conn:
        _initialize(conn)
    return {"state": "initialized", "database": str(db_path)}


def _dispatch(args: argparse.Namespace, db_path: Path) -> dict | list[dict]:
    handlers = {
        "init": lambda: _initialize_ledger(db_path),
        "create": lambda: create_task(db_path, args.title, args.description, args.dependencies),
        "list": lambda: list_tasks(db_path),
        "show": lambda: get_task(db_path, args.task_id),
        "start": lambda: transition_task(db_path, args.task_id, "IN_PROGRESS", args.details),
        "unblock": lambda: transition_task(db_path, args.task_id, "PENDING", args.details),
        "complete": lambda: transition_task(db_path, args.task_id, "COMPLETED", args.evidence),
        "block": lambda: transition_task(db_path, args.task_id, "BLOCKED", args.reason),
        "fail": lambda: transition_task(db_path, args.task_id, "FAILED", args.details),
    }
    return handlers[args.command]()


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        db_path = _db_path(args.project_root, args.state_file)
        result = _dispatch(args, db_path)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (TaskLedgerError, sqlite3.Error, OSError, ValueError) as exc:
        print(f"task-ledger error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
