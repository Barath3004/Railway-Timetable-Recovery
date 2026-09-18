"""
Wikipedia Infobox Parser

Purpose
-------
Extract every field from a Wikipedia infobox and return
them as a Python dictionary.

Responsibilities
----------------
1. Find the Wikipedia infobox.
2. Extract the infobox title.
3. Extract every key-value pair.
4. Clean extracted text.

This module DOES NOT:
---------------------
- Rename fields.
- Convert data types.
- Decide which fields are important.
"""

import re

from bs4 import BeautifulSoup


class WikipediaParser:
    """Parses Wikipedia station pages."""

    def clean_text(self, text: str) -> str:
        """
        Clean extracted Wikipedia text.

        Removes:
        - Citation markers like [1], [12]
        - Extra spaces
        - Newlines
        """

        if not text:
            return ""

        # Remove citation markers
        text = re.sub(r"\[\s*\d+\s*\]", "", text)

        # Replace multiple whitespace/newlines with one space
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    def parse_infobox(self, html: str) -> dict:
        """
        Extract every field from the Wikipedia infobox.

        Parameters
        ----------
        html : str
            HTML page downloaded from Wikipedia.

        Returns
        -------
        dict
            Dictionary containing every extracted field.
        """

        soup = BeautifulSoup(html, "html.parser")

        infobox = soup.find("table", class_="infobox")

        if infobox is None:
            raise Exception("Wikipedia infobox not found.")

        data = {}

        # ----------------------------------------
        # Extract infobox title
        # ----------------------------------------

        title = infobox.find("th", class_="infobox-above")

        if title:
            data["Station Name"] = self.clean_text(
                title.get_text(" ", strip=True)
            )

        # ----------------------------------------
        # Extract every key-value row
        # ----------------------------------------

        rows = infobox.find_all("tr")

        for row in rows:

            header = row.find("th")
            value = row.find("td")

            if header and value:

                key = self.clean_text(
                    header.get_text(" ", strip=True)
                )

                val = self.clean_text(
                    value.get_text(" ", strip=True)
                )

                data[key] = val

        return data