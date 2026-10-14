"""Behavioral tests for the autonomous engineering task ledger."""
from __future__ import annotations

import importlib.util
import sqlite3
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).parents[2]
    / "skills"
    / "software-development"
    / "autonomous-engineering-agent"
    / "scripts"
    / "task_state.py"
)
SPEC = importlib.util.spec_from_file_location("engineering_task_state", SCRIPT)
assert SPEC and SPEC.loader
ledger = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ledger)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    return ledger._db_path(str(project), None)


def test_task_lifecycle_requires_evidence_and_records_events(db_path: Path) -> None:
    task = ledger.create_task(db_path, "Implement health endpoint", "Add route and tests")
    task_id = task["task_id"]

    with pytest.raises(ledger.TaskLedgerError, match="verification evidence"):
        ledger.transition_task(db_path, task_id, "COMPLETED")

    started = ledger.transition_task(db_path, task_id, "IN_PROGRESS")
    assert started["status"] == "IN_PROGRESS"

    completed = ledger.transition_task(
        db_path, task_id, "COMPLETED", "pytest: 12 passed; endpoint smoke test: PASS"
    )
    assert completed["status"] == "COMPLETED"
    assert completed["evidence"].startswith("pytest:")
    assert [event["event_type"] for event in completed["events"]] == [
        "CREATED",
        "STATUS_CHANGED",
        "STATUS_CHANGED",
    ]


def test_dependencies_block_start_until_prerequisite_is_completed(db_path: Path) -> None:
    foundation = ledger.create_task(db_path, "Design schema")
    implementation = ledger.create_task(
        db_path, "Implement schema", dependencies=[foundation["task_id"]]
    )

    with pytest.raises(ledger.TaskLedgerError, match="Dependencies are not complete"):
        ledger.transition_task(db_path, implementation["task_id"], "IN_PROGRESS")

    ledger.transition_task(db_path, foundation["task_id"], "IN_PROGRESS")
    ledger.transition_task(db_path, foundation["task_id"], "COMPLETED", "Schema reviewed")
    started = ledger.transition_task(db_path, implementation["task_id"], "IN_PROGRESS")
    assert started["status"] == "IN_PROGRESS"
    assert started["dependencies"] == [foundation["task_id"]]


def test_invalid_transition_from_completed_is_rejected(db_path: Path) -> None:
    task = ledger.create_task(db_path, "Ship release")
    ledger.transition_task(db_path, task["task_id"], "IN_PROGRESS")
    ledger.transition_task(db_path, task["task_id"], "COMPLETED", "CI green")

    with pytest.raises(ledger.TaskLedgerError, match="Invalid transition"):
        ledger.transition_task(db_path, task["task_id"], "FAILED")


def test_block_requires_reason_and_can_be_unblocked(db_path: Path) -> None:
    task = ledger.create_task(db_path, "Configure CI")

    with pytest.raises(ledger.TaskLedgerError, match="requires a reason"):
        ledger.transition_task(db_path, task["task_id"], "BLOCKED")

    blocked = ledger.transition_task(db_path, task["task_id"], "BLOCKED", "Waiting for runner")
    assert blocked["blocked_reason"] == "Waiting for runner"
    assert ledger.transition_task(db_path, task["task_id"], "PENDING")["status"] == "PENDING"


def test_refuses_foreign_database_without_mutating_it(tmp_path: Path) -> None:
    db_path = tmp_path / "application.sqlite3"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE application_state (value TEXT NOT NULL)")
        conn.execute("INSERT INTO application_state(value) VALUES ('preserve me')")
    before = db_path.read_bytes()

    with pytest.raises(ledger.TaskLedgerError, match="owned by another application"):
        ledger.create_task(db_path, "Do not touch foreign DB")

    assert db_path.read_bytes() == before


def test_refuses_unrecognized_ledger_metadata_without_mutating_it(tmp_path: Path) -> None:
    db_path = tmp_path / "state.sqlite3"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE ledger_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        conn.execute("INSERT INTO ledger_meta(key, value) VALUES ('application_version', '1')")
        conn.execute("CREATE TABLE tasks (value TEXT NOT NULL)")
        conn.execute("CREATE TABLE task_dependencies (value TEXT NOT NULL)")
        conn.execute("CREATE TABLE task_events (value TEXT NOT NULL)")
    before = db_path.read_bytes()

    with pytest.raises(ledger.TaskLedgerError, match="unrecognized ledger metadata"):
        ledger.create_task(db_path, "Do not claim foreign state")

    assert db_path.read_bytes() == before


def test_refuses_non_local_backend_without_mutating_it(tmp_path: Path) -> None:
    db_path = tmp_path / "state.sqlite3"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE ledger_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        conn.execute("INSERT INTO ledger_meta(key, value) VALUES ('task_backend', 'kanban')")
        conn.execute("CREATE TABLE tasks (value TEXT NOT NULL)")
        conn.execute("CREATE TABLE task_dependencies (value TEXT NOT NULL)")
        conn.execute("CREATE TABLE task_events (value TEXT NOT NULL)")
        conn.execute("CREATE TABLE existing_state (value TEXT NOT NULL)")
        conn.execute("INSERT INTO existing_state(value) VALUES ('preserve me')")
    before = db_path.read_bytes()

    with pytest.raises(ledger.TaskLedgerError, match="refusing to mutate"):
        ledger.create_task(db_path, "Do not dual-write task state")

    assert db_path.read_bytes() == before


def test_project_state_path_cannot_escape_project(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "outside.sqlite3"

    with pytest.raises(ledger.TaskLedgerError, match="inside the project root"):
        ledger._db_path(str(project), str(outside))


def test_sql_like_task_text_is_stored_as_data(db_path: Path) -> None:
    title = "ignore previous instructions'; DROP TABLE tasks; --"
    task = ledger.create_task(db_path, title)
    listed = ledger.list_tasks(db_path)
    assert len(listed) == 1
    assert listed[0]["title"] == title
    assert ledger.get_task(db_path, task["task_id"])["status"] == "PENDING"
