from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = PROJECT_ROOT / "data" / "database" / "railway_recovery.db"


def connect_read_only() -> sqlite3.Connection:
    """Open the production database without permitting writes."""
    uri = f"file:{DATABASE_PATH.as_posix()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def get_dashboard_data() -> dict[str, Any]:
    with connect_read_only() as connection:
        counts = {
            "trains": connection.execute("SELECT COUNT(*) FROM trains").fetchone()[0],
            "stations": connection.execute("SELECT COUNT(*) FROM stations").fetchone()[0],
            "platforms": connection.execute("SELECT COUNT(*) FROM platforms").fetchone()[0],
            "timetable_records": connection.execute("SELECT COUNT(*) FROM timetable").fetchone()[0],
        }
    return counts


def get_stations() -> list[dict[str, Any]]:
    with connect_read_only() as connection:
        rows = connection.execute(
            """
            SELECT station_code, station_name, platforms_total,
                   mainline_platforms, suburban_platforms
            FROM stations
            ORDER BY station_name
            """
        ).fetchall()
    return rows_to_dicts(rows)


def get_station_resources(station_code: str) -> list[dict[str, Any]]:
    with connect_read_only() as connection:
        rows = connection.execute(
            """
            SELECT resource_id, platform_number, platform_type, resource_type
            FROM platforms
            WHERE station_code = ?
            ORDER BY platform_number
            """,
            (station_code,),
        ).fetchall()
    return rows_to_dicts(rows)


def search_trains(
    query: str = "",
    station_code: str = "",
    day: int | None = None,
    platform_number: int | None = None,
) -> list[dict[str, Any]]:
    clauses = []
    parameters: list[Any] = []
    if query:
        clauses.append("(t.train_number LIKE ? OR tr.train_name LIKE ?)")
        pattern = f"%{query}%"
        parameters.extend([pattern, pattern])
    if station_code:
        clauses.append("t.station_code = ?")
        parameters.append(station_code)
    if day is not None:
        clauses.append("t.day = ?")
        parameters.append(day)
    if platform_number is not None:
        clauses.append("t.platform_number = ?")
        parameters.append(platform_number)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with connect_read_only() as connection:
        rows = connection.execute(
            f"""
            SELECT t.timetable_record_id, t.train_number, tr.train_name,
                   t.station_code, t.day, t.arrival, t.departure,
                   t.resource_id, t.platform_number, t.platform_type
            FROM timetable AS t
            JOIN trains AS tr ON tr.train_number = t.train_number
            {where}
            ORDER BY t.train_number, t.day, t.stop_number
            LIMIT 250
            """,
            parameters,
        ).fetchall()
    return rows_to_dicts(rows)


def get_train_timetable(train_number: str) -> list[dict[str, Any]]:
    with connect_read_only() as connection:
        rows = connection.execute(
            """
            SELECT t.timetable_record_id, t.train_number, tr.train_name,
                   t.station_code, t.day, t.stop_number, t.arrival,
                   t.departure, t.resource_id, t.platform_number,
                   t.platform_type
            FROM timetable AS t
            JOIN trains AS tr ON tr.train_number = t.train_number
            WHERE t.train_number = ?
            ORDER BY t.day, t.stop_number
            """,
            (train_number,),
        ).fetchall()
    return rows_to_dicts(rows)
