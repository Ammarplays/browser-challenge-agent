#!/usr/bin/env python3
"""Quick peek at the challenge site"""

import asyncio
from playwright.async_api import async_playwright

async def peek():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 720})
        
        await page.goto("https://serene-frangipane-7fd25b.netlify.app/", wait_until="networkidle")
        await asyncio.sleep(2)
        
        # Screenshot
        await page.screenshot(path="challenge_preview.png")
        print("📸 Saved: challenge_preview.png")
        
        # Get page content
        content = await page.content()
        text = await page.inner_text("body")
        print("\n📄 Page text:")
        print(text[:2000])
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(peek())
