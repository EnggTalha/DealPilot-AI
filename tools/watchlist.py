"""
tools/watchlist.py — Manage the product watchlist (add, remove, list).
Products stored as JSON in data/products/.
"""

from __future__ import annotations
import json
import uuid
from pathlib import Path
from typing import List, Optional
from rich.console import Console
from rich.table import Table
from rich import box

from config import WatchlistItem, PRODUCTS_DIR

console = Console()
WATCHLIST_FILE = PRODUCTS_DIR / "watchlist.json"


def load_watchlist() -> List[WatchlistItem]:
    """Load all products from watchlist."""
    if not WATCHLIST_FILE.exists():
        return _seed_demo_watchlist()
    try:
        with open(WATCHLIST_FILE) as f:
            data = json.load(f)
        return [WatchlistItem(**item) for item in data]
    except Exception as e:
        console.print(f"[red]Watchlist load error:[/red] {e}")
        return []


def save_watchlist(items: List[WatchlistItem]) -> None:
    with open(WATCHLIST_FILE, "w") as f:
        json.dump([i.model_dump() for i in items], f, indent=2)


def add_product(
    name: str,
    urls: List[str],
    target_price: Optional[float] = None,
    drop_threshold: float = 10.0,
    max_price: Optional[float] = None,
    priority: str = "normal",
    notes: str = "",
    auto_buy: bool = False,
    tags: List[str] = None,
) -> WatchlistItem:
    """Add a product to the watchlist."""
    items = load_watchlist()

    item = WatchlistItem(
        id=str(uuid.uuid4())[:8],
        name=name,
        urls=urls,
        target_price=target_price,
        drop_threshold=drop_threshold,
        max_price=max_price,
        priority=priority,
        notes=notes,
        auto_buy=auto_buy,
        tags=tags or [],
    )
    items.append(item)
    save_watchlist(items)
    console.print(f"[green]✓[/green] Added '[bold]{name}[/bold]' to watchlist (id: {item.id})")
    return item


def remove_product(product_id: str) -> bool:
    items = load_watchlist()
    before = len(items)
    items = [i for i in items if i.id != product_id]
    if len(items) < before:
        save_watchlist(items)
        console.print(f"[green]✓[/green] Removed product {product_id}")
        return True
    console.print(f"[red]Product {product_id} not found.[/red]")
    return False


def print_watchlist(items: List[WatchlistItem]) -> None:
    """Print watchlist as a Rich table."""
    if not items:
        console.print("[yellow]Watchlist is empty. Add products with --add.[/yellow]")
        return

    table = Table(
        title=f"📋 Watchlist ({len(items)} products)",
        box=box.ROUNDED, border_style="cyan", show_lines=True,
    )
    table.add_column("ID",       width=8)
    table.add_column("Product",  max_width=30)
    table.add_column("Target $", justify="right", width=10)
    table.add_column("Drop %",   justify="right", width=8)
    table.add_column("Priority", width=10)
    table.add_column("Platforms", max_width=25)

    priority_color = {"urgent": "red", "high": "orange3", "normal": "white", "low": "dim"}
    for item in items:
        platforms = ", ".join(_detect_platform(u) for u in item.urls)
        color = priority_color.get(item.priority, "white")
        table.add_row(
            f"[dim]{item.id}[/dim]",
            f"[{color}]{item.name}[/{color}]",
            f"${item.target_price:.2f}" if item.target_price else "—",
            f"{item.drop_threshold:.0f}%",
            f"[{color}]{item.priority}[/{color}]",
            platforms,
        )
    console.print(table)


def _detect_platform(url: str) -> str:
    url = url.lower()
    if "amazon"     in url: return "Amazon"
    if "ebay"       in url: return "eBay"
    if "aliexpress" in url: return "AliExpress"
    if "daraz"      in url: return "Daraz"
    if "walmart"    in url: return "Walmart"
    if "bestbuy"    in url: return "BestBuy"
    return "Web"


def _seed_demo_watchlist() -> List[WatchlistItem]:
    """Create a demo watchlist for first-time users."""
    items = [
        WatchlistItem(
            id="demo001",
            name="Sony WH-1000XM5 Headphones",
            urls=[
                "https://www.amazon.com/dp/B09XS7JWHH",
                "https://www.ebay.com/itm/sony-wh1000xm5",
            ],
            target_price=280.0,
            drop_threshold=10.0,
            max_price=350.0,
            priority="high",
            notes="Been watching for 3 months",
            tags=["audio", "electronics"],
        ),
        WatchlistItem(
            id="demo002",
            name="iPhone 15 Pro 256GB",
            urls=["https://www.amazon.com/dp/B0CHX2F5QT"],
            target_price=900.0,
            drop_threshold=5.0,
            max_price=1100.0,
            priority="normal",
            tags=["phone", "apple"],
        ),
        WatchlistItem(
            id="demo003",
            name="Logitech MX Master 3S Mouse",
            urls=[
                "https://www.amazon.com/dp/B09HM94VDS",
                "https://www.bestbuy.com/site/logitech-mx-master-3s",
            ],
            target_price=80.0,
            drop_threshold=15.0,
            auto_buy=True,
            priority="low",
            notes="Auto-buy if under $80",
            tags=["peripherals", "work"],
        ),
    ]
    save_watchlist(items)
    console.print("[dim]Created demo watchlist with 3 products.[/dim]")
    return items
