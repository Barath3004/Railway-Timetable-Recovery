"""
Test Passenger Mapper

This script tests the PassengerMapper by:

1. Extracting rows from a passenger PDF.
2. Cleaning them using PassengerMapper.
3. Printing summary information.
"""

from data.passenger.pdf_extractor import PassengerPDFExtractor
from data.passenger.mappers.chennai_mapper import ChennaiMapper


PDF_PATH = "data/raw/chennai_division.pdf"



def main():

    # ---------------------------------------------
    # Extract raw rows from PDF
    # ---------------------------------------------
    extractor = PassengerPDFExtractor()

    rows = extractor.extract_tables(PDF_PATH)

    # ---------------------------------------------
    # Map rows
    # ---------------------------------------------
    mapper = ChennaiMapper(
    rows=rows,
    division="Chennai"

    )

    records = mapper.map_rows()

    # ---------------------------------------------
    # Summary
    # ---------------------------------------------
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    print(f"Raw Rows       : {len(rows)}")
    print(f"Mapped Records : {len(records)}")

    # ---------------------------------------------
    # First 10 records
    # ---------------------------------------------
    print("\nFIRST 10 RECORDS")
    print("-" * 60)

    for record in records[:10]:
        print(record)

    # ---------------------------------------------
    # Last 5 records
    # ---------------------------------------------
    print("\nLAST 5 RECORDS")
    print("-" * 60)

    for record in records[-5:]:
        print(record)


if __name__ == "__main__":
    main()