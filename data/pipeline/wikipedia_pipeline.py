"""
Wikipedia ETL Pipeline

Purpose
-------
Runs the complete Wikipedia ETL process for all
configured stations.

Pipeline
--------
Station URLs
    ↓
Downloader
    ↓
Parser
    ↓
Mapper
    ↓
Station Builder
    ↓
CSV Exporter
"""

from data.config.station_urls import STATIONS

from data.wikipedia.wikipedia_downloader import WikipediaDownloader
from data.wikipedia.wikipedia_parser import WikipediaParser
from data.wikipedia.wikipedia_mapper import WikipediaMapper
from data.wikipedia.station_builder import StationBuilder

from data.exporter.wikipedia_exporter import WikipediaExporter


class WikipediaPipeline:

    def __init__(self):

        self.downloader = WikipediaDownloader()
        self.parser = WikipediaParser()
        self.exporter = WikipediaExporter()

    def run(self):

        station_records = []

        print("=" * 60)
        print("Wikipedia ETL Started")
        print("=" * 60)

        for station in STATIONS:

            print(f"\nProcessing {station['station_code']}...")

            try:

                # -----------------------------------
                # Download Wikipedia page
                # -----------------------------------

                html = self.downloader.download_page(
                    station["url"]
                )

                # -----------------------------------
                # Parse Infobox
                # -----------------------------------

                parsed_data = self.parser.parse_infobox(html)

                # -----------------------------------
                # Map Wikipedia fields
                # -----------------------------------

                mapper = WikipediaMapper(parsed_data)

                mapped_data = mapper.map_all()

                # -----------------------------------
                # Build Station Record
                # -----------------------------------

                builder = StationBuilder()

                builder.add_wikipedia_data(mapped_data)

                station_record = builder.build()

                station_records.append(station_record)

                print("[SUCCESS] Station processed.")

            except Exception as e:

                print(f"[FAILED] {station['station_code']}")

                print(e)

        # -------------------------------------------
        # Export CSV
        # -------------------------------------------

        output_file = "data/master/station_wikipedia.csv"

        self.exporter.export(
            station_records,
            output_file
        )

        print("\nWikipedia ETL Completed.")


if __name__ == "__main__":

    pipeline = WikipediaPipeline()

    pipeline.run()