"""
Configuration file for the Railway Station Scraper.

This file contains all configurable settings used by the scraper.
If you want to change delays, headers, or URLs, do it here.
"""

# Base website
BASE_URL = "https://indiarailinfo.com"

# Request timeout (seconds)
REQUEST_TIMEOUT = 15

# Delay between requests (seconds)
REQUEST_DELAY = 2

# User-Agent to simulate a normal browser
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/138.0.0.0 Safari/537.36"
    )
}