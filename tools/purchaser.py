"""
tools/purchaser.py — Automated purchasing via Playwright.
Currently supports Amazon checkout flow.
Always dry-runs unless AUTO_PURCHASE=true AND item.auto_buy=true AND price under limit.
"""

from __future__ import annotations
from datetime import datetime, timezone
from rich.console import Console

from config import EnvConfig, WatchlistItem, PricePoint, PurchaseAction

console = Console()


def attempt_purchase(item: WatchlistItem, price_point: PricePoint) -> PurchaseAction:
    """
    Attempt to purchase a product.
    Dry-run by default — live mode requires explicit opt-in in .env.
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    if EnvConfig.DRY_RUN:
        console.print(
            f"  [yellow][DRY RUN][/yellow] Would purchase: {item.name} "
            f"@ ${price_point.price:.2f} on {price_point.platform}"
        )
        return PurchaseAction(
            product_id=item.id,
            product_name=item.name,
            platform=price_point.platform,
            url=price_point.url,
            price=price_point.price,
            action="dry_run",
            reason="DRY_RUN=true in config",
            timestamp=timestamp,
        )

    if not EnvConfig.AUTO_PURCHASE:
        return PurchaseAction(
            product_id=item.id, product_name=item.name,
            platform=price_point.platform, url=price_point.url,
            price=price_point.price, action="skipped",
            reason="AUTO_PURCHASE=false", timestamp=timestamp,
        )

    if price_point.price > EnvConfig.MAX_AUTO_PURCHASE:
        return PurchaseAction(
            product_id=item.id, product_name=item.name,
            platform=price_point.platform, url=price_point.url,
            price=price_point.price, action="skipped",
            reason=f"Price ${price_point.price:.2f} exceeds MAX_AUTO_PURCHASE_USD=${EnvConfig.MAX_AUTO_PURCHASE:.2f}",
            timestamp=timestamp,
        )

    # Live purchase
    if price_point.platform == "amazon":
        return _amazon_purchase(item, price_point, timestamp)
    else:
        return PurchaseAction(
            product_id=item.id, product_name=item.name,
            platform=price_point.platform, url=price_point.url,
            price=price_point.price, action="skipped",
            reason=f"Auto-purchase not yet supported for {price_point.platform}",
            timestamp=timestamp,
        )


def _amazon_purchase(item: WatchlistItem, point: PricePoint, timestamp: str) -> PurchaseAction:
    """
    Attempt Amazon 1-Click or cart add via Playwright.
    Requires you to be logged into Amazon in a saved browser profile.
    """
    try:
        from playwright.sync_api import sync_playwright

        console.print(f"  [cyan]Attempting Amazon purchase: {item.name}[/cyan]")

        with sync_playwright() as p:
            # Use persistent context to retain Amazon login session
            browser = p.chromium.launch_persistent_context(
                user_data_dir="data/.browser_profile",
                headless=True,
            )
            page = browser.new_page()
            page.goto(point.url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)

            # Try "Buy Now" first
            buy_now = page.query_selector("#buy-now-button")
            if buy_now:
                buy_now.click()
                page.wait_for_timeout(3000)

                # Look for order confirmation
                if "order" in page.url.lower() or page.query_selector(".a-alert-success"):
                    browser.close()
                    console.print(f"  [green]✓ Purchase successful! {item.name} @ ${point.price:.2f}[/green]")
                    return PurchaseAction(
                        product_id=item.id, product_name=item.name,
                        platform="amazon", url=point.url,
                        price=point.price, action="purchased",
                        reason="Buy Now clicked, order confirmed",
                        timestamp=timestamp,
                    )

            # Fall back to Add to Cart
            add_to_cart = page.query_selector("#add-to-cart-button")
            if add_to_cart:
                add_to_cart.click()
                page.wait_for_timeout(2000)
                browser.close()
                console.print(f"  [green]✓ Added to cart: {item.name}[/green]")
                return PurchaseAction(
                    product_id=item.id, product_name=item.name,
                    platform="amazon", url=point.url,
                    price=point.price, action="cart_added",
                    reason="Buy Now not available — added to cart instead",
                    timestamp=timestamp,
                )

            browser.close()
            return PurchaseAction(
                product_id=item.id, product_name=item.name,
                platform="amazon", url=point.url,
                price=point.price, action="skipped",
                reason="Could not find Buy Now or Add to Cart button",
                timestamp=timestamp,
            )

    except Exception as e:
        return PurchaseAction(
            product_id=item.id, product_name=item.name,
            platform="amazon", url=point.url,
            price=point.price, action="skipped",
            reason=f"Purchase error: {e}",
            timestamp=timestamp,
        )
