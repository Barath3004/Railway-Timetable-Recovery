"""
Wikipedia CSV Exporter

Purpose
-------
Exports processed Wikipedia station data
to a CSV file.

Responsibility
--------------
Only writes CSV files.
"""

import csv
import os


class WikipediaExporter:

    def export(self, stations, output_file):

        if not stations:
            print("[WARNING] No station data to export.")
            return

        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        fieldnames = list(stations[0].keys())

        with open(
            output_file,
            "w",
            newline="",
            encoding="utf-8"
        ) as csvfile:

            writer = csv.DictWriter(
                csvfile,
                fieldnames=fieldnames
            )

            writer.writeheader()

            for station in stations:
                writer.writerow(station)

        print(f"[SUCCESS] Exported {len(stations)} stations.")
        print(f"[FILE] {output_file}")