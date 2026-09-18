"""
Passenger PDF Configuration

Purpose
-------
Contains the list of passenger division PDF files
used by the Passenger ETL pipeline.

Responsibilities
----------------
1. Store PDF file locations.
2. Store division names.
3. Allow the pipeline to iterate through every PDF.
"""

PDF_FILES = [

    {
        "division": "Chennai",
        "file": "data/raw/chennai_division.pdf"
    },

    {
        "division": "Madurai",
        "file": "data/raw/madurai_division.pdf"
    },

    {
        "division": "Thiruvananthapuram",
        "file": "data/raw/thiruvananthapuram_division.pdf"
    }

]