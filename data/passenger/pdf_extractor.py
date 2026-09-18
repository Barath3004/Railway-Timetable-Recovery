"""
Passenger PDF Extractor

Purpose
-------
Extracts tabular data from railway passenger PDF reports.

Responsibilities
----------------
1. Open a PDF.
2. Read every page.
3. Extract all tables.
4. Return rows as dictionaries.

This module DOES NOT:
---------------------
- Clean values.
- Rename columns.
- Convert data types.
- Export CSV.
"""

import pdfplumber


class PassengerPDFExtractor:
    """Extracts tables from passenger statistics PDFs."""

    def extract_tables(self, pdf_path: str) -> list:
        """
        Extract all table rows from a PDF.

        Parameters
        ----------
        pdf_path : str
            Path to the PDF file.

        Returns
        -------
        list
            List of table rows.
            Each row is returned exactly as extracted.
        """

        print(f"[INFO] Reading PDF: {pdf_path}")

        extracted_rows = []

        with pdfplumber.open(pdf_path) as pdf:

            print(f"[INFO] Total Pages : {len(pdf.pages)}")

            for page_number, page in enumerate(pdf.pages, start=1):

                print(f"[INFO] Processing Page {page_number}")

                tables = page.extract_tables()

                if not tables:
                    continue

                for table in tables:

                    if table is None:
                        continue

                    for row in table:

                        if row:
                            extracted_rows.append(row)

        print(f"[SUCCESS] Extracted {len(extracted_rows)} rows.")

        return extracted_rows