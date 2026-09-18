"""
Chennai Passenger Mapper

Purpose
-------
Converts Chennai division station category PDF
into standard passenger schema.
"""


import re


class ChennaiMapper:


    def __init__(self, rows, division):

        self.rows = rows
        self.division = division
        self.cleaned = []


    def is_header_row(self, row):

        if not row:
            return True

        return str(row[0]).strip() == "Sl.\nNo."


    def is_title_row(self, row):

        if not row:
            return True

        return False


    def is_total_row(self, row):

        if not row:
            return True

        return False



    def clean_station_name(self, name):

        if not name:
            return ""

        name = re.sub(
            r"\(HALT\)",
            "",
            str(name),
            flags=re.IGNORECASE
        )

        return " ".join(name.split())



    def map_rows(self):


        for row in self.rows:


            if self.is_header_row(row):
                continue


            if self.is_title_row(row):
                continue


            if len(row) < 4:
                continue


            record = {

                "division": self.division,

                "station_name":
                    self.clean_station_name(row[1]),

                "station_code":
                    row[2],

                "district":
                    None,

                "state":
                    "Tamil Nadu",

                "category":
                    row[3],

                "old_category":
                    None,

                "annual_earnings":
                    None,

                "annual_passengers":
                    None,

                "daily_earnings":
                    None,

                "daily_passengers":
                    None,

                "footfall":
                    None

            }


            self.cleaned.append(record)


        return self.cleaned