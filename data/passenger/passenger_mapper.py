"""
Passenger Mapper

Converts raw PDF table rows into the project's
standard passenger schema.

Responsibilities
----------------
1. Remove repeated header rows.
2. Remove summary/total rows.
3. Clean station names.
4. Clean numeric values.
5. Return standardized dictionary records.
"""

import re


class PassengerMapper:

    def __init__(self, rows, division):

        self.rows = rows
        self.division = division
        self.cleaned = []

    # -------------------------------------------------------
    # Helpers
    # -------------------------------------------------------

    def is_header_row(self, row):
        """
        Detect repeated table headers.
        """

        if not row:
            return True

        first = str(row[0]).strip()

        return first == "S.\nNo."

    def is_total_row(self, row):
        """
        Detect grand total row.
        """

        if not row:
            return True

        return row[0] is None

    def clean_station_name(self, name):
        """
        Remove FLAG/HALT labels
        and normalize common abbreviations.
        """

        if not name:
            return ""

        name = re.sub(r"\(FLAG\)", "", name, flags=re.IGNORECASE)
        name = re.sub(r"\(HALT\)", "", name, flags=re.IGNORECASE)

        replacements = {
            " jn": " Junction",
            " Jn": " Junction",
            " JN": " Junction"
        }

        for old, new in replacements.items():
            name = name.replace(old, new)

        return " ".join(name.split())

    def clean_number(self, value):
        """
        Convert numbers into integers.

        Examples
        --------
        1,86,61,83,588 -> 1866183588
        Gauge Conversion -> None
        """

        if value is None:
            return None

        value = str(value).strip()

        if value == "":
            return None

        if "Gauge" in value:
            return None

        value = value.replace(",", "")

        if value.isdigit():
            return int(value)

        return None

    # -------------------------------------------------------
    # Mapping
    # -------------------------------------------------------

    def map_rows(self):

        for row in self.rows:

            if self.is_header_row(row):
                continue

            if self.is_total_row(row):
                continue

            if len(row) < 11:
                continue

            record = {

                "division": self.division,

                "station_name": self.clean_station_name(row[1]),

                "station_code": row[2],

                "district": row[3],

                "state": row[4],

                "category": row[5],

                "annual_earnings": self.clean_number(row[6]),

                "annual_passengers": self.clean_number(row[7]),

                "daily_earnings": self.clean_number(row[8]),

                "daily_passengers": self.clean_number(row[9]),

                "footfall": self.clean_number(row[10])

            }

            self.cleaned.append(record)

        return self.cleaned