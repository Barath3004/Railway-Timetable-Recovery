from __future__ import annotations

import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = PROJECT_ROOT / "data" / "database" / "railway_recovery.db"


def main() -> None:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    try:
        print("BUFFER ANALYSIS")
        print("=" * 60)

        # 1. Overall buffer distribution
        print("\n1. BUFFER DISTRIBUTION")
        print("-" * 60)

        rows = connection.execute(
            """
            SELECT
                buffer_minutes,
                COUNT(*) AS allocation_count
            FROM resource_allocations
            GROUP BY buffer_minutes
            ORDER BY buffer_minutes
            """
        ).fetchall()

        for row in rows:
            print(
                f"Buffer {row['buffer_minutes']:>3} min"
                f" -> {row['allocation_count']:>5} allocations"
            )

        # 2. Zero-dwell records
        print("\n2. ZERO-DWELL RECORDS")
        print("-" * 60)

        rows = connection.execute(
            """
            SELECT
                ra.buffer_minutes,
                COUNT(*) AS allocation_count
            FROM resource_allocations ra
            JOIN timetable t
                ON t.timetable_record_id = ra.timetable_record_id
            WHERE
                t.arrival IS NOT NULL
                AND t.departure IS NOT NULL
                AND t.arrival = t.departure
            GROUP BY ra.buffer_minutes
            ORDER BY ra.buffer_minutes
            """
        ).fetchall()

        for row in rows:
            print(
                f"Buffer {row['buffer_minutes']:>3} min"
                f" -> {row['allocation_count']:>5} zero-dwell allocations"
            )

        # 3. Origin records: arrival is NULL
        print("\n3. ORIGIN / DEPARTURE-ONLY RECORDS")
        print("-" * 60)

        rows = connection.execute(
            """
            SELECT
                ra.buffer_minutes,
                COUNT(*) AS allocation_count
            FROM resource_allocations ra
            JOIN timetable t
                ON t.timetable_record_id = ra.timetable_record_id
            WHERE t.arrival IS NULL
              AND t.departure IS NOT NULL
            GROUP BY ra.buffer_minutes
            ORDER BY ra.buffer_minutes
            """
        ).fetchall()

        for row in rows:
            print(
                f"Buffer {row['buffer_minutes']:>3} min"
                f" -> {row['allocation_count']:>5} origin allocations"
            )

        # 4. Non-zero dwell records
        print("\n4. NON-ZERO DWELL RECORDS")
        print("-" * 60)

        rows = connection.execute(
            """
            SELECT
                ra.buffer_minutes,
                COUNT(*) AS allocation_count
            FROM resource_allocations ra
            JOIN timetable t
                ON t.timetable_record_id = ra.timetable_record_id
            WHERE
                t.arrival IS NOT NULL
                AND t.departure IS NOT NULL
                AND t.arrival != t.departure
            GROUP BY ra.buffer_minutes
            ORDER BY ra.buffer_minutes
            """
        ).fetchall()

        for row in rows:
            print(
                f"Buffer {row['buffer_minutes']:>3} min"
                f" -> {row['allocation_count']:>5} non-zero-dwell allocations"
            )

        # 5. Examples of zero-dwell allocations
        print("\n5. SAMPLE ZERO-DWELL ALLOCATIONS")
        print("-" * 60)

        rows = connection.execute(
            """
            SELECT
                ra.timetable_record_id,
                t.train_number,
                t.station_code,
                t.arrival,
                t.departure,
                ra.resource_id,
                ra.allocation_start,
                ra.allocation_end,
                ra.occupancy_minutes,
                ra.buffer_minutes,
                ra.release_time
            FROM resource_allocations ra
            JOIN timetable t
                ON t.timetable_record_id = ra.timetable_record_id
            WHERE
                t.arrival IS NOT NULL
                AND t.departure IS NOT NULL
                AND t.arrival = t.departure
            ORDER BY ra.buffer_minutes, ra.timetable_record_id
            LIMIT 15
            """
        ).fetchall()

        for row in rows:
            print(
                f"ID={row['timetable_record_id']} | "
                f"Train={row['train_number']} | "
                f"Station={row['station_code']} | "
                f"Time={row['arrival']} | "
                f"Resource={row['resource_id']} | "
                f"Buffer={row['buffer_minutes']} | "
                f"Release={row['release_time']}"
            )

        # 6. Examples of origin allocations
        print("\n6. SAMPLE ORIGIN ALLOCATIONS")
        print("-" * 60)

        rows = connection.execute(
            """
            SELECT
                ra.timetable_record_id,
                t.train_number,
                t.station_code,
                t.departure,
                ra.resource_id,
                ra.allocation_start,
                ra.allocation_end,
                ra.occupancy_minutes,
                ra.buffer_minutes,
                ra.release_time
            FROM resource_allocations ra
            JOIN timetable t
                ON t.timetable_record_id = ra.timetable_record_id
            WHERE t.arrival IS NULL
              AND t.departure IS NOT NULL
            ORDER BY ra.buffer_minutes, ra.timetable_record_id
            LIMIT 15
            """
        ).fetchall()

        for row in rows:
            print(
                f"ID={row['timetable_record_id']} | "
                f"Train={row['train_number']} | "
                f"Station={row['station_code']} | "
                f"Departure={row['departure']} | "
                f"Resource={row['resource_id']} | "
                f"Buffer={row['buffer_minutes']} | "
                f"Release={row['release_time']}"
            )

    finally:
        connection.close()


if __name__ == "__main__":
    main()