import asyncio
from playwright.async_api import async_playwright
from typing import List
from .models import ScraperSource

async def fetch_pdf_links(source: ScraperSource) -> List[str]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(source.base_url, wait_until="networkidle")
        # Encontrar links a PDFs
        links = await page.eval_on_selector_all(
            source.link_selector,
            "elements => elements.map(e => e.href)"
        )
        await browser.close()
        return links
