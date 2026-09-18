"""
Main file for testing Playwright.
"""

from browser import open_page


def main():

    url = "https://indiarailinfo.com/departures/mgr-chennai-central-mas/35"

    playwright, browser, page = open_page(url)

    print("\n========== PAGE TITLE ==========")
    print(page.title())
    print("================================")

    input("\nPress ENTER to close browser...")

    browser.close()
    playwright.stop()


if __name__ == "__main__":
    main()