from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUTH_ROOT = PROJECT_ROOT / "output" / "webapp" / "auth"
AUTH_DB = AUTH_ROOT / "auth.db"


class AuthStore:
    def __init__(self, db_path: Path = AUTH_DB) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.db_path), timeout=30)
        connection.row_factory = sqlite3.Row
        return connection

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode=WAL;

                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    password_salt TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_login_at TEXT
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token_hash TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    revoked INTEGER NOT NULL DEFAULT 0,
                    ip_address TEXT,
                    user_agent TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS inference_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    task_type TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    model_id TEXT,
                    model_label TEXT,
                    detection_count INTEGER NOT NULL DEFAULT 0,
                    latency_seconds REAL NOT NULL DEFAULT 0,
                    record_id TEXT,
                    summary_json TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );

                CREATE INDEX IF NOT EXISTS idx_sessions_token_hash ON sessions(token_hash);
                CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
                CREATE INDEX IF NOT EXISTS idx_inference_audit_user_created ON inference_audit(user_id, created_at DESC);
                """
            )
            self._ensure_column(connection, "inference_audit", "model_id", "TEXT")
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_inference_audit_user_model ON inference_audit(user_id, model_id)"
            )

    def _ensure_column(self, connection: sqlite3.Connection, table_name: str, column_name: str, column_type: str) -> None:
        columns = {
            row["name"]
            for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        }
        if column_name in columns:
            return
        connection.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
        )

    def count_users(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(1) AS count FROM users").fetchone()
        return int(row["count"]) if row else 0

    def create_user(
        self,
        username: str,
        password_hash: str,
        password_salt: str,
        created_at: str,
    ) -> Dict[str, Any]:
        with self._lock:
            with self._connect() as connection:
                cursor = connection.cursor()
                try:
                    cursor.execute(
                        """
                        INSERT INTO users (username, password_hash, password_salt, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (username, password_hash, password_salt, created_at, created_at),
                    )
                except sqlite3.IntegrityError as exc:
                    raise ValueError("Username already exists.") from exc
                user_id = cursor.lastrowid
                row = cursor.execute(
                    "SELECT id, username, created_at, updated_at, last_login_at FROM users WHERE id = ?",
                    (user_id,),
                ).fetchone()
        if row is None:
            raise ValueError("Failed to create user.")
        return dict(row)

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM users WHERE username = ?",
                (username,),
            ).fetchone()
        return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        return dict(row) if row else None

    def update_password(
        self,
        user_id: int,
        password_hash: str,
        password_salt: str,
        updated_at: str,
    ) -> None:
        with self._lock:
            with self._connect() as connection:
                connection.execute(
                    """
                    UPDATE users
                    SET password_hash = ?, password_salt = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (password_hash, password_salt, updated_at, user_id),
                )

    def touch_last_login(self, user_id: int, login_at: str) -> None:
        with self._lock:
            with self._connect() as connection:
                connection.execute(
                    "UPDATE users SET last_login_at = ? WHERE id = ?",
                    (login_at, user_id),
                )

    def create_session(
        self,
        user_id: int,
        token_hash: str,
        created_at: str,
        expires_at: str,
        ip_address: Optional[str],
        user_agent: Optional[str],
    ) -> Dict[str, Any]:
        with self._lock:
            with self._connect() as connection:
                cursor = connection.cursor()
                cursor.execute(
                    """
                    INSERT INTO sessions (
                        user_id,
                        token_hash,
                        created_at,
                        expires_at,
                        revoked,
                        ip_address,
                        user_agent
                    )
                    VALUES (?, ?, ?, ?, 0, ?, ?)
                    """,
                    (user_id, token_hash, created_at, expires_at, ip_address, user_agent),
                )
                session_id = cursor.lastrowid
                row = cursor.execute(
                    "SELECT * FROM sessions WHERE id = ?",
                    (session_id,),
                ).fetchone()
        if row is None:
            raise ValueError("Failed to create user session.")
        return dict(row)

    def get_session_by_token_hash(self, token_hash: str) -> Optional[Dict[str, Any]]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    s.id AS session_id,
                    s.token_hash,
                    s.created_at AS session_created_at,
                    s.expires_at,
                    s.revoked,
                    s.ip_address,
                    s.user_agent,
                    u.id AS user_id,
                    u.username,
                    u.created_at AS user_created_at,
                    u.updated_at AS user_updated_at,
                    u.last_login_at,
                    u.password_hash,
                    u.password_salt
                FROM sessions s
                INNER JOIN users u ON u.id = s.user_id
                WHERE s.token_hash = ?
                LIMIT 1
                """,
                (token_hash,),
            ).fetchone()
        return dict(row) if row else None

    def revoke_session(self, token_hash: str) -> None:
        with self._lock:
            with self._connect() as connection:
                connection.execute(
                    "UPDATE sessions SET revoked = 1 WHERE token_hash = ?",
                    (token_hash,),
                )

    def revoke_sessions_for_user(self, user_id: int) -> None:
        with self._lock:
            with self._connect() as connection:
                connection.execute(
                    "UPDATE sessions SET revoked = 1 WHERE user_id = ?",
                    (user_id,),
                )

    def purge_expired_sessions(self, now_iso: str) -> int:
        with self._lock:
            with self._connect() as connection:
                cursor = connection.execute(
                    "DELETE FROM sessions WHERE expires_at <= ? OR revoked = 1",
                    (now_iso,),
                )
        return int(cursor.rowcount or 0)

    def add_inference_audit(
        self,
        user_id: int,
        task_type: str,
        source_name: str,
        model_id: str,
        model_label: str,
        detection_count: int,
        latency_seconds: float,
        record_id: str,
        summary_json: str,
        created_at: str,
    ) -> None:
        with self._lock:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO inference_audit (
                        user_id,
                        task_type,
                        source_name,
                        model_id,
                        model_label,
                        detection_count,
                        latency_seconds,
                        record_id,
                        summary_json,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        task_type,
                        source_name,
                        model_id,
                        model_label,
                        detection_count,
                        latency_seconds,
                        record_id,
                        summary_json,
                        created_at,
                    ),
                )

    def list_inference_audit(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    task_type,
                    source_name,
                    model_id,
                    model_label,
                    detection_count,
                    latency_seconds,
                    record_id,
                    summary_json,
                    created_at
                FROM inference_audit
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]
