from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HISTORY_PATH = PROJECT_ROOT / "data" / "database" / "recovery_history.db"


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(HISTORY_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS recovery_operations (
            operation_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            disruption_json TEXT NOT NULL,
            affected_trains INTEGER NOT NULL,
            options_json TEXT NOT NULL,
            selected_option INTEGER,
            status TEXT NOT NULL,
            metrics_json TEXT NOT NULL
        )
        """
    )
    connection.commit()
    return connection


def record_operation(
    operation_id: str,
    disruption: dict[str, Any],
    affected_trains: int,
    options: list[dict[str, Any]],
    metrics: dict[str, Any],
    selected_option: int,
) -> dict[str, Any]:
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO recovery_operations
            (operation_id, created_at, disruption_json, affected_trains,
             options_json, selected_option, status, metrics_json)
            VALUES (?, ?, ?, ?, ?, ?, 'CONFIRMED', ?)
            """,
            (
                operation_id,
                created_at,
                json.dumps(disruption),
                affected_trains,
                json.dumps(options),
                selected_option,
                json.dumps(metrics),
            ),
        )
        connection.commit()
    return get_operation(operation_id) or {}


def get_operation(operation_id: str) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM recovery_operations WHERE operation_id = ?",
            (operation_id,),
        ).fetchone()
    if row is None:
        return None
    return _decode(row)


def list_operations(limit: int = 50) -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            "SELECT * FROM recovery_operations ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [_decode(row) for row in rows]


def _decode(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["disruption"] = json.loads(item.pop("disruption_json"))
    item["options"] = json.loads(item.pop("options_json"))
    item["metrics"] = json.loads(item.pop("metrics_json"))
    return item
