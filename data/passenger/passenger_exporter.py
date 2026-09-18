"""
Passenger CSV Exporter

Purpose
-------
Exports the final passenger dataset into a CSV file.

Responsibilities
----------------
1. Receive cleaned passenger records.
2. Create the output directory if needed.
3. Save the records as a CSV file.
"""

from pathlib import Path
import csv


class PassengerExporter:

    def __init__(self, output_path):

        self.output_path = Path(output_path)

    def export(self, records):

        # Create folder if it doesn't exist
        self.output_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        if not records:
            print("[WARNING] No records to export.")
            return

        # --------------------------------------------------
        # Collect all unique field names from every record
        # --------------------------------------------------

        fieldnames = []

        for record in records:

            for key in record.keys():

                if key not in fieldnames:
                    fieldnames.append(key)

        # --------------------------------------------------
        # Write CSV
        # --------------------------------------------------

        with open(
            self.output_path,
            mode="w",
            newline="",
            encoding="utf-8"
        ) as csv_file:

            writer = csv.DictWriter(
                csv_file,
                fieldnames=fieldnames,
                extrasaction="ignore"
            )

            writer.writeheader()

            writer.writerows(records)

        print("\n" + "=" * 60)
        print("PASSENGER CSV CREATED")
        print("=" * 60)
        print(f"Location : {self.output_path}")
        print(f"Rows     : {len(records)}")