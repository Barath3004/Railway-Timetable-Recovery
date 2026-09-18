"""
Thiruvananthapuram Passenger Mapper

Purpose
-------
Converts extracted Thiruvananthapuram division PDF rows
into the project's standard passenger schema.

Responsibilities
----------------
1. Remove repeated headers.
2. Remove title rows.
3. Remove total rows.
4. Clean station names.
5. Clean numeric values.
6. Return standardized dictionary records.
"""

import re


class TVMMapper:

    def __init__(self, rows, division):

        self.rows = rows
        self.division = division
        self.cleaned = []


    # -------------------------------------------------------
    # Header / invalid row detection
    # -------------------------------------------------------

    def is_header_row(self, row):
        """
        Detect repeated table headers.
        """

        if not row:
            return True

        first = str(row[0]).strip()

        return first == "S.\nNo."


    def is_title_row(self, row):
        """
        Remove PDF title rows.
        """

        if not row:
            return True

        text = str(row[0])

        if "Annual Originating" in text:
            return True

        if "Category based" in text:
            return True

        return False


    def is_total_row(self, row):
        """
        Detect final total row.
        """

        if not row:
            return True

        # Usually station name will be empty
        if len(row) > 1:
            if row[1] is None:
                return True

            if str(row[1]).strip() == "":
                return True

        return False



    # -------------------------------------------------------
    # Cleaning helpers
    # -------------------------------------------------------

    def clean_station_name(self, name):

        if not name:
            return ""

        name = str(name).strip()

        name = re.sub(
            r"\s+jn$",
            " Junction",
            name,
            flags=re.IGNORECASE
        )

        return " ".join(name.split())



    def clean_number(self, value):

        if value is None:
            return None

        value = str(value).strip()

        if value == "":
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


            if self.is_title_row(row):
                continue


            if self.is_header_row(row):
                continue


            if self.is_total_row(row):
                continue


            # TVM should contain 12 columns
            if len(row) < 11:
                continue



            record = {


                "division": self.division,


                "station_name":
                    self.clean_station_name(row[1]),


                "station_code":
                    row[2],


                "district":
                    row[3],


                "state":
                    row[4],


                "category":
                    row[5],


                "old_category":
                    row[6],


                "annual_earnings":
                    self.clean_number(row[7]),


                "annual_passengers":
                    self.clean_number(row[8]),


                "daily_earnings":
                    self.clean_number(row[9]),


                "daily_passengers":
                    self.clean_number(row[10]),


                "footfall":
                    None

            }


            self.cleaned.append(record)


        return self.cleaned