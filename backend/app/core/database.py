from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS swarm_plans (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    objective TEXT NOT NULL,
    topology TEXT NOT NULL,
    max_agents INTEGER NOT NULL,
    routing_mode TEXT NOT NULL,
    critical_path_steps INTEGER NOT NULL,
    total_mcp_calls INTEGER NOT NULL,
    flat_tier3_tokens INTEGER NOT NULL,
    selective_routed_tokens INTEGER NOT NULL,
    token_reduction_pct REAL NOT NULL,
    parallel_efficiency_pct REAL NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_swarm_plans_topology ON swarm_plans(topology);
CREATE INDEX IF NOT EXISTS idx_swarm_plans_routing_mode ON swarm_plans(routing_mode);
CREATE INDEX IF NOT EXISTS idx_swarm_plans_created_at ON swarm_plans(created_at DESC);

CREATE TABLE IF NOT EXISTS benchmark_runs (
    id TEXT PRIMARY KEY,
    suite_name TEXT NOT NULL,
    horizon_threshold INTEGER NOT NULL,
    mcp_call_threshold INTEGER NOT NULL,
    case_count INTEGER NOT NULL,
    routing_accuracy_pct REAL NOT NULL,
    baseline_total_tokens INTEGER NOT NULL,
    routed_total_tokens INTEGER NOT NULL,
    overall_token_reduction_pct REAL NOT NULL,
    avg_overhead_ms REAL NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    detail TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


class DatabaseManager:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._lock = threading.RLock()
        self._memory_conn: sqlite3.Connection | None = None
        self.initialize()

    def _connect(self) -> sqlite3.Connection:
        if self.db_path == ":memory:":
            if self._memory_conn is None:
                self._memory_conn = sqlite3.connect(":memory:", check_same_thread=False)
                self._memory_conn.row_factory = sqlite3.Row
                self._memory_conn.execute("PRAGMA foreign_keys = ON;")
            return self._memory_conn

        target = Path(self.db_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(target), timeout=15.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    def initialize(self) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.executescript(SCHEMA_SQL)
                conn.commit()
            finally:
                if self.db_path != ":memory:":
                    conn.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            conn = self._connect()
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                if self.db_path != ":memory:":
                    conn.close()
