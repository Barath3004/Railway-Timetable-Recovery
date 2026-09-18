"""
Wikipedia Downloader

Purpose:
--------
Downloads the HTML page of a Wikipedia railway station.

Responsibility:
---------------
Only downloads the page.
No parsing.
No CSV writing.
"""

import requests


class WikipediaDownloader:
    """Handles downloading Wikipedia pages."""

    def __init__(self):
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/137.0 Safari/537.36"
            )
        }

    def download_page(self, url: str) -> str:
        """
        Downloads the HTML content of a Wikipedia page.

        Parameters
        ----------
        url : str
            Wikipedia page URL.

        Returns
        -------
        str
            HTML content.

        Raises
        ------
        Exception
            If the page cannot be downloaded.
        """

        print(f"[INFO] Downloading: {url}")

        response = requests.get(
            url,
            headers=self.headers,
            timeout=30
        )

        response.raise_for_status()

        print("[SUCCESS] Page downloaded successfully.")

        return response.text