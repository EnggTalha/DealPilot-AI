"""
main.py — CLI entry point for the Autonomous Price Scout Agent.

Usage:
  python main.py                              # run once (dry run)
  python main.py --watch                      # run continuously every N minutes
  python main.py --add                        # interactive: add product to watchlist
  python main.py --list                       # show watchlist
  python main.py --remove <id>               # remove product from watchlist
  python main.py --live                       # live mode (real alerts + purchases)
"""

import argparse
import sys
from rich.console import Console
from config import EnvConfig

console = Console()


def validate_env() -> bool:
    if not EnvConfig.ANTHROPIC_API_KEY:
        console.print("[bold red]Error:[/bold red] ANTHROPIC_API_KEY is not set.")
        console.print("Copy [dim].env.example[/dim] → [dim].env[/dim] and add your key.")
        return False
    return True


def interactive_add():
    """Guided CLI to add a product to the watchlist."""
    from tools.watchlist import add_product
    console.print("\n[bold cyan]➕ Add Product to Watchlist[/bold cyan]\n")

    name = input("Product name: ").strip()
    if not name:
        console.print("[red]Name is required.[/red]")
        return

    urls_input = input("Product URL(s) — comma-separated (Amazon, eBay, etc.): ").strip()
    urls = [u.strip() for u in urls_input.split(",") if u.strip()]
    if not urls:
        console.print("[red]At least one URL is required.[/red]")
        return

    target_str = input("Target price (leave blank to skip): $").strip()
    target = float(target_str) if target_str else None

    drop_str = input("Alert on price drop of (%) [default: 10]: ").strip()
    drop = float(drop_str) if drop_str else 10.0

    max_str = input("Max price willing to pay (leave blank to skip): $").strip()
    max_p = float(max_str) if max_str else None

    priority = input("Priority [low/normal/high/urgent, default: normal]: ").strip() or "normal"
    notes    = input("Notes (optional): ").strip()
    auto_buy = input("Auto-buy when criteria met? [y/N]: ").strip().lower() == "y"
    tags_str = input("Tags (comma-separated, optional): ").strip()
    tags     = [t.strip() for t in tags_str.split(",") if t.strip()]

    add_product(
        name=name, urls=urls, target_price=target,
        drop_threshold=drop, max_price=max_p,
        priority=priority, notes=notes,
        auto_buy=auto_buy, tags=tags,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Autonomous Price Scout Agent — powered by Claude"
    )
    parser.add_argument("--watch",   action="store_true", help="Run continuously on a schedule")
    parser.add_argument("--add",     action="store_true", help="Interactively add a product")
    parser.add_argument("--list",    action="store_true", help="Show watchlist")
    parser.add_argument("--remove",  type=str,            help="Remove product by ID")
    parser.add_argument("--dry-run", action="store_true", help="Simulate — no real alerts or purchases")
    parser.add_argument("--live",    action="store_true", help="Live mode — real alerts and purchases")
    parser.add_argument("--interval",type=int,            help="Check interval in minutes (overrides .env)")
    args = parser.parse_args()

    if args.dry_run:  EnvConfig.DRY_RUN = True
    if args.live:     EnvConfig.DRY_RUN = False
    if args.interval: EnvConfig.CHECK_INTERVAL = args.interval

    # Commands that don't need the API key
    if args.list:
        from tools.watchlist import load_watchlist, print_watchlist
        print_watchlist(load_watchlist())
        return

    if args.add:
        interactive_add()
        return

    if args.remove:
        from tools.watchlist import remove_product
        remove_product(args.remove)
        return

    if not validate_env():
        sys.exit(1)

    from agent.orchestrator import PriceScoutAgent
    agent = PriceScoutAgent()

    if args.watch:
        agent.run_continuous()
    else:
        agent.run()


if __name__ == "__main__":
    main()
