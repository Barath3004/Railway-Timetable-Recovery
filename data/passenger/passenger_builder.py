"""
Passenger Dataset Builder

Purpose
-------
Combines passenger information from different
railway divisions into one unified dataset.

Responsibilities
----------------
1. Extract PDF data.
2. Apply correct mapper.
3. Combine all records.
4. Remove duplicate stations.
5. Return final passenger dataset.
"""


from data.passenger.pdf_extractor import PassengerPDFExtractor

from data.passenger.passenger_mapper import PassengerMapper
from data.passenger.mappers.tvm_mapper import TVMMapper
from data.passenger.mappers.chennai_mapper import ChennaiMapper



class PassengerBuilder:


    def __init__(self):

        self.extractor = PassengerPDFExtractor()

        self.records = []



    def process_division(self, pdf_path, division):

        print("\n" + "=" * 60)
        print(f"Processing {division}")
        print("=" * 60)


        rows = self.extractor.extract_tables(pdf_path)


        if division == "Thiruvananthapuram":

            mapper = TVMMapper(
                rows,
                division
            )


        elif division == "Chennai":

            mapper = ChennaiMapper(
                rows,
                division
            )


        else:

            mapper = PassengerMapper(
                rows,
                division
            )


        mapped_records = mapper.map_rows()


        print(
            f"{division} Records : {len(mapped_records)}"
        )


        self.records.extend(mapped_records)



    def remove_duplicates(self):

        unique = {}

        for record in self.records:

            key = record["station_code"]


            if key not in unique:

                unique[key] = record


        self.records = list(unique.values())



    def build(self):

        self.remove_duplicates()

        return self.records