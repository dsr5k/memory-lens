from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    file_path TEXT NOT NULL,
    start_ms INTEGER NOT NULL,
    end_ms INTEGER NOT NULL,
    source TEXT NOT NULL,
    device_id TEXT,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
);
"""


def _connect(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db(db_path: Path) -> None:
    with _connect(db_path) as conn:
        conn.executescript(SCHEMA)
        conn.commit()


def create_session(db_path: Path, session_id: str, created_at: str) -> dict[str, Any]:
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO sessions(session_id, created_at) VALUES(?, ?)",
            (session_id, created_at),
        )
        conn.commit()
    return {"session_id": session_id, "created_at": created_at}


def get_session(db_path: Path, session_id: str) -> dict[str, Any] | None:
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT session_id, created_at FROM sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
    return dict(row) if row else None


def create_chunk(db_path: Path, chunk: dict[str, Any]) -> dict[str, Any]:
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO chunks(
                chunk_id, session_id, file_path, start_ms, end_ms,
                source, device_id, status, created_at, updated_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chunk["chunk_id"],
                chunk["session_id"],
                chunk["file_path"],
                chunk["start_ms"],
                chunk["end_ms"],
                chunk["source"],
                chunk["device_id"],
                chunk["status"],
                chunk["created_at"],
                chunk["updated_at"],
            ),
        )
        conn.commit()
    return chunk


def update_chunk_status(db_path: Path, chunk_id: str, status: str, updated_at: str) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            "UPDATE chunks SET status = ?, updated_at = ? WHERE chunk_id = ?",
            (status, updated_at, chunk_id),
        )
        conn.commit()


def list_chunks_by_session(db_path: Path, session_id: str) -> list[dict[str, Any]]:
    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT
                chunk_id, session_id, file_path, start_ms, end_ms,
                source, device_id, status, created_at, updated_at
            FROM chunks
            WHERE session_id = ?
            ORDER BY created_at ASC
            """,
            (session_id,),
        ).fetchall()
    return [dict(row) for row in rows]
