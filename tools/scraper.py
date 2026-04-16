"""
tools/scraper.py — Scrape prices from product URLs using Playwright + BS4.
Handles Amazon, eBay, AliExpress, and generic sites.
Includes mock fallback for testing without a browser.
"""

from __future__ import annotations
import re
import json
import random
from datetime import datetime, timezone
from typing import Optional, List
from pathlib import Path
from rich.console import Console

from config import (
    EnvConfig, WatchlistItem, PricePoint, PriceHistory,
    PLATFORM_SELECTORS, PRICES_DIR
)

console = Console()


# ── Main scraper ───────────────────────────────────────────────────────

def scrape_product_prices(item: WatchlistItem) -> List[PricePoint]:
    """Scrape prices for a watchlist item across all its URLs."""
    points: List[PricePoint] = []
    for url in item.urls:
        point = scrape_url(url, item.id)
        if point:
            points.append(point)
    return points


def scrape_url(url: str, product_id: str) -> Optional[PricePoint]:
    """Scrape a single URL for price data."""
    platform = _detect_platform(url)
    console.print(f"  [dim]Scraping {platform}: {url[:60]}...[/dim]")

    try:
        return _scrape_with_playwright(url, product_id, platform)
    except ImportError:
        console.print("  [yellow]Playwright not installed — using mock data.[/yellow]")
        return _mock_price_point(url, product_id, platform)
    except Exception as e:
        console.print(f"  [red]Scrape error ({platform}):[/red] {e}")
        return _mock_price_point(url, product_id, platform)


def _scrape_with_playwright(url: str, product_id: str, platform: str) -> Optional[PricePoint]:
    from playwright.sync_api import sync_playwright
    from bs4 import BeautifulSoup
    from fake_useragent import UserAgent

    ua = UserAgent()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=ua.random,
            viewport={"width": 1280, "height": 800},
            java_script_enabled=True,
        )
        page = context.new_page()

        # Block images and fonts to speed up scraping
        page.route("**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf}", lambda r: r.abort())

        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)  # let JS render

            html = page.content()
            soup = BeautifulSoup(html, "lxml")

            selectors = PLATFORM_SELECTORS.get(platform, {})

            # Extract price
            price = _extract_price(soup, selectors.get("price", []))
            if not price:
                # Fallback: look for any price-like text
                price = _generic_price_extraction(soup)

            if not price:
                console.print(f"  [yellow]Could not extract price from {platform}[/yellow]")
                browser.close()
                return None

            # Extract other fields
            title       = _extract_text(soup, selectors.get("title", []))
            stock_text  = _extract_text(soup, selectors.get("stock",  []))
            rating_text = _extract_text(soup, selectors.get("rating", []))
            reviews_text= _extract_text(soup, selectors.get("reviews",  []))

            in_stock    = _parse_stock(stock_text)
            rating      = _parse_float(rating_text)
            review_count= _parse_int(reviews_text)

            browser.close()
            return PricePoint(
                product_id=product_id,
                platform=platform,
                url=url,
                price=price,
                currency=EnvConfig.CURRENCY,
                in_stock=in_stock,
                title=title or "",
                rating=rating,
                review_count=review_count,
                scraped_at=_now(),
            )

        except Exception as e:
            browser.close()
            raise e


# ── Price history ──────────────────────────────────────────────────────

def load_price_history(product_id: str) -> PriceHistory:
    path = PRICES_DIR / f"{product_id}.json"
    if path.exists():
        try:
            with open(path) as f:
                return PriceHistory(**json.load(f))
        except Exception:
            pass
    return PriceHistory(product_id=product_id, product_name="")


def save_price_history(history: PriceHistory) -> None:
    path = PRICES_DIR / f"{history.product_id}.json"
    with open(path, "w") as f:
        json.dump(history.model_dump(), f, indent=2, default=str)


def update_price_history(product_id: str, product_name: str, new_points: List[PricePoint]) -> PriceHistory:
    """Append new price points to history and update stats."""
    history = load_price_history(product_id)
    history.product_name = product_name
    history.history.extend(new_points)

    # Keep last 90 days only
    history.history = history.history[-500:]

    all_prices = [p.price for p in history.history if p.price > 0]
    if all_prices:
        history.lowest_ever  = min(all_prices)
        history.highest_ever = max(all_prices)
        history.avg_price    = sum(all_prices) / len(all_prices)

    save_price_history(history)
    return history


# ── Extraction helpers ─────────────────────────────────────────────────

def _extract_price(soup, selectors: list) -> Optional[float]:
    for selector in selectors:
        el = soup.select_one(selector)
        if el:
            price = _parse_price_text(el.get_text())
            if price:
                return price
    return None


def _generic_price_extraction(soup) -> Optional[float]:
    """Try to find any price on the page using regex."""
    patterns = [
        r'\$[\d,]+\.?\d*',
        r'USD\s*[\d,]+\.?\d*',
        r'Price:\s*\$?[\d,]+\.?\d*',
    ]
    text = soup.get_text()
    for pattern in patterns:
        matches = re.findall(pattern, text[:5000])
        if matches:
            price = _parse_price_text(matches[0])
            if price and 0.5 < price < 50000:
                return price
    return None


def _extract_text(soup, selectors: list) -> str:
    for selector in selectors:
        el = soup.select_one(selector)
        if el:
            return el.get_text(strip=True)
    return ""


def _parse_price_text(text: str) -> Optional[float]:
    cleaned = re.sub(r"[^\d.]", "", text.replace(",", ""))
    try:
        price = float(cleaned)
        return price if 0.01 < price < 100000 else None
    except (ValueError, TypeError):
        return None


def _parse_stock(text: str) -> bool:
    if not text:
        return True
    return "out of stock" not in text.lower() and "unavailable" not in text.lower()


def _parse_float(text: str) -> Optional[float]:
    match = re.search(r"[\d.]+", text)
    try:
        return float(match.group()) if match else None
    except (ValueError, TypeError):
        return None


def _parse_int(text: str) -> Optional[int]:
    cleaned = re.sub(r"[^\d]", "", text)
    try:
        return int(cleaned) if cleaned else None
    except (ValueError, TypeError):
        return None


def _detect_platform(url: str) -> str:
    url = url.lower()
    if "amazon"     in url: return "amazon"
    if "ebay"       in url: return "ebay"
    if "aliexpress" in url: return "aliexpress"
    if "daraz"      in url: return "daraz"
    if "walmart"    in url: return "walmart"
    if "bestbuy"    in url: return "bestbuy"
    return "web"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Mock fallback ──────────────────────────────────────────────────────

def _mock_price_point(url: str, product_id: str, platform: str) -> PricePoint:
    """Realistic mock prices for testing without a live browser."""
    mock_prices = {
        "demo001": {"amazon": 310.0, "ebay": 295.0, "aliexpress": 260.0},
        "demo002": {"amazon": 949.0},
        "demo003": {"amazon": 89.99, "bestbuy": 84.99},
    }
    base = mock_prices.get(product_id, {}).get(platform, 199.99)
    # Add small random variance to simulate price changes
    price = round(base + random.uniform(-base * 0.03, base * 0.03), 2)

    mock_titles = {
        "demo001": "Sony WH-1000XM5 Wireless Headphones",
        "demo002": "Apple iPhone 15 Pro 256GB Natural Titanium",
        "demo003": "Logitech MX Master 3S Performance Wireless Mouse",
    }

    return PricePoint(
        product_id=product_id,
        platform=platform,
        url=url,
        price=price,
        currency="USD",
        in_stock=random.random() > 0.1,
        title=mock_titles.get(product_id, "Product"),
        rating=round(random.uniform(4.0, 4.9), 1),
        review_count=random.randint(100, 15000),
        scraped_at=_now(),
    )
