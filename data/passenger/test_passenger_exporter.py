"""
Test Passenger Exporter
"""

from data.passenger.passenger_builder import PassengerBuilder
from data.passenger.passenger_exporter import PassengerExporter


def main():

    builder = PassengerBuilder()

    builder.process_division(
        "data/raw/madurai_division.pdf",
        "Madurai"
    )

    builder.process_division(
        "data/raw/thiruvananthapuram_division.pdf",
        "Thiruvananthapuram"
    )

    builder.process_division(
        "data/raw/chennai_division.pdf",
        "Chennai"
    )

    records = builder.build()

    exporter = PassengerExporter(
        "data/processed/passenger/passenger_station_data.csv"
    )

    exporter.export(records)


if __name__ == "__main__":
    main()