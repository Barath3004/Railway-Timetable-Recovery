"""
Browser Module

Responsible for launching Microsoft Edge using Playwright.
"""

from playwright.sync_api import sync_playwright


EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


def open_page(url: str):

    playwright = sync_playwright().start()

    browser = playwright.chromium.launch(
        executable_path=EDGE_PATH,
        headless=False,
        slow_mo=500
    )

    page = browser.new_page()

    print(f"[INFO] Opening: {url}")

    page.goto(
        url,
        wait_until="domcontentloaded",
        timeout=60000
    )

    print("[SUCCESS] Page Loaded Successfully")

    return playwright, browser, page