"""
Station Builder

Purpose
-------
Combines station information collected from multiple
data sources into one complete station record.

Sources
-------
1. Wikipedia
2. Passenger Dataset / PDF
3. Timetable Dataset

Output
------
One dictionary representing a complete station.
"""


class StationBuilder:

    def __init__(self):
        self.station = {}

    def add_wikipedia_data(self, wiki_data: dict):
        """Merge Wikipedia data."""
        self.station.update(wiki_data)

    def add_passenger_data(self, passenger_data: dict):
        """Merge passenger statistics."""
        self.station.update(passenger_data)

    def add_timetable_data(self, timetable_data: dict):
        """Merge timetable information."""
        self.station.update(timetable_data)

    def build(self):
        """Return the completed station record."""
        return self.station