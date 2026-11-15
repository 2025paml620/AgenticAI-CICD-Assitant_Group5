"""Capture full-page screenshots of the dashboard for every scenario.

Owner: Member 4 (Karthik).

    streamlit run app.py --server.port 8599 --server.headless true   # terminal 1
    pip install playwright                                           # once
    python scripts/capture_screenshots.py                            # terminal 2

Uses the locally installed Google Chrome (channel="chrome"); run
`playwright install chromium` and drop `channel` if Chrome is not installed.
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "docs" / "screenshots"
URL = "http://localhost:8599/?scenario={}&run=1"

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome")
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    for sid in "ABCDE":
        page.goto(URL.format(sid))
        page.get_by_text("Agent decisions and reasoning").wait_for(timeout=180_000)  # LLM can be slow
        page.wait_for_timeout(1500)
        height = page.evaluate("document.querySelector('[data-testid=stMainBlockContainer]')?.scrollHeight || 3000")
        page.set_viewport_size({"width": 1440, "height": int(height) + 100})
        page.wait_for_timeout(1000)
        page.screenshot(path=str(OUT / f"scenario_{sid}.png"))
        page.set_viewport_size({"width": 1440, "height": 900})
        print(f"Saved {OUT / f'scenario_{sid}.png'}")
    browser.close()
