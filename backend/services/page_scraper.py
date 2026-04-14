"""
Playwright-based landing page scraper.

Extracts structured content useful for ad coherence scoring:
- Page title, H1, H2s, meta description
- Above-the-fold visible text (first viewport)
- CTA button text
- Promotional offer mentions
- Load time, mobile-friendliness
- Screenshot (PNG bytes, caller decides where to store)
"""

import asyncio
import re
import time
from dataclasses import dataclass, field
from typing import Optional

from playwright.async_api import async_playwright, Page, TimeoutError as PWTimeout

OFFER_PATTERNS = re.compile(
    r"""
    (\$[\d,]+(?:\.\d{2})?\s*off)       |  # $X off
    (\d+%\s*off)                        |  # X% off
    (free\s+shipping)                   |  # free shipping
    (free\s+trial)                      |  # free trial
    (free\s+\w+)                        |  # free <something>
    (save\s+\$[\d,]+)                   |  # save $X
    (save\s+\d+%)                       |  # save X%
    (buy\s+\d+\s*,?\s*get\s+\d+)       |  # buy X get Y
    (limited\s+time)                    |  # limited time
    (expires?\s+soon)                   |  # expires soon
    (\d+\s*days?\s+free)               |  # X days free
    (no\s+credit\s+card)                  # no credit card
    """,
    re.IGNORECASE | re.VERBOSE,
)


@dataclass
class ScrapedPage:
    url: str
    page_title: str = ""
    h1: str = ""
    h2s: list[str] = field(default_factory=list)
    meta_description: str = ""
    above_fold_text: str = ""
    cta_texts: list[str] = field(default_factory=list)
    offer_mentions: list[str] = field(default_factory=list)
    load_time_ms: int = 0
    mobile_friendly: bool = False
    screenshot_bytes: Optional[bytes] = None
    error: Optional[str] = None


async def _extract_content(page: Page) -> dict:
    """Run JS inside the page to extract structured content."""
    return await page.evaluate("""
        () => {
            const getText = (el) => el ? el.innerText.trim() : "";
            const getAttr = (el, attr) => el ? (el.getAttribute(attr) || "").trim() : "";

            // H1 — first one only
            const h1 = getText(document.querySelector("h1"));

            // H2s — up to 10
            const h2s = Array.from(document.querySelectorAll("h2"))
                .slice(0, 10)
                .map(el => getText(el))
                .filter(t => t.length > 0);

            // Meta description
            const metaDesc = getAttr(
                document.querySelector('meta[name="description"]'),
                "content"
            );

            // Above the fold: grab text from elements in the first viewport
            const vw = window.innerWidth;
            const vh = window.innerHeight;
            const aboveFoldElements = Array.from(document.querySelectorAll("p, h1, h2, h3, span, li, div"))
                .filter(el => {
                    const rect = el.getBoundingClientRect();
                    // Must be visible (non-zero area) and within the viewport
                    return rect.top >= 0 && rect.bottom <= vh &&
                           rect.left >= 0 && rect.right <= vw &&
                           rect.width > 0 && rect.height > 0 &&
                           el.children.length === 0; // Leaf nodes only to avoid duplication
                })
                .map(el => getText(el))
                .filter(t => t.length > 3);
            const aboveFoldText = [...new Set(aboveFoldElements)].join(" ").substring(0, 3000);

            // CTA buttons: <button> and <a> elements that look like buttons
            const ctaSelectors = [
                "button",
                'a[class*="btn"]',
                'a[class*="button"]',
                'a[class*="cta"]',
                'input[type="submit"]',
                'input[type="button"]',
            ];
            const ctaTexts = Array.from(
                new Set(
                    ctaSelectors.flatMap(sel =>
                        Array.from(document.querySelectorAll(sel))
                            .map(el => getText(el) || getAttr(el, "value"))
                            .filter(t => t.length > 0 && t.length < 80)
                    )
                )
            ).slice(0, 15);

            return { h1, h2s, metaDesc, aboveFoldText, ctaTexts };
        }
    """)


async def scrape_page(url: str, timeout_ms: int = 30_000) -> ScrapedPage:
    """
    Scrape a single URL. Returns a ScrapedPage; on error sets .error and
    returns partial data where available.
    """
    result = ScrapedPage(url=url)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            # --- Desktop scrape ---
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            page = await context.new_page()

            t0 = time.monotonic()
            try:
                await page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            except PWTimeout:
                # Fallback: accept whatever loaded within the timeout
                pass
            load_time_ms = int((time.monotonic() - t0) * 1000)

            result.page_title = await page.title()
            content = await _extract_content(page)

            result.h1 = content["h1"]
            result.h2s = content["h2s"]
            result.meta_description = content["metaDesc"]
            result.above_fold_text = content["aboveFoldText"]
            result.cta_texts = content["ctaTexts"]
            result.load_time_ms = load_time_ms

            # Find offer mentions in the full page text
            full_text = await page.inner_text("body")
            offers = list({m.group(0) for m in OFFER_PATTERNS.finditer(full_text)})
            result.offer_mentions = offers[:20]

            # Screenshot (full viewport)
            result.screenshot_bytes = await page.screenshot(type="jpeg", quality=70)

            await context.close()

            # --- Mobile check ---
            mobile_context = await browser.new_context(
                viewport={"width": 375, "height": 812},
                user_agent=(
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                    "Version/16.0 Mobile/15E148 Safari/604.1"
                ),
            )
            mobile_page = await mobile_context.new_page()
            try:
                await mobile_page.goto(url, wait_until="networkidle", timeout=15_000)
            except PWTimeout:
                pass

            # Heuristic: page is "mobile friendly" if the viewport meta tag is present
            # and the content doesn't overflow horizontally
            mobile_check = await mobile_page.evaluate("""
                () => {
                    const vp = document.querySelector('meta[name="viewport"]');
                    const hasViewport = vp && vp.content.includes("width=device-width");
                    const bodyWidth = document.body ? document.body.scrollWidth : 9999;
                    return hasViewport && bodyWidth <= window.innerWidth + 20;
                }
            """)
            result.mobile_friendly = bool(mobile_check)
            await mobile_context.close()

        except Exception as exc:
            result.error = str(exc)
        finally:
            await browser.close()

    return result


async def scrape_pages_batch(urls: list[str], concurrency: int = 3) -> dict[str, ScrapedPage]:
    """
    Scrape multiple URLs with bounded concurrency.
    Returns {url: ScrapedPage}.
    """
    semaphore = asyncio.Semaphore(concurrency)

    async def scrape_with_limit(url: str) -> tuple[str, ScrapedPage]:
        async with semaphore:
            page = await scrape_page(url)
            return url, page

    results = await asyncio.gather(*[scrape_with_limit(u) for u in urls])
    return dict(results)
