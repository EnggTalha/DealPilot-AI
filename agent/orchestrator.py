"""
agent/orchestrator.py — Main agentic loop for the Price Scout.

Flow per run:
1. Load watchlist
2. For each product: scrape all platform URLs
3. Update price history
4. Claude analyzes deal quality (score 0-100, buy/wait/skip verdict)
5. Decide whether to alert (respects drop threshold, no spam)
6. Optionally auto-purchase if criteria met
7. Print report + save Markdown
"""

from __future__ import annotations
from rich.console import Console
from rich.panel import Panel

from config import EnvConfig
from tools.watchlist import load_watchlist, print_watchlist
from tools.scraper import scrape_product_prices, update_price_history
from tools.alerter import send_alert, should_send_alert, load_last_alert_price
from tools.purchaser import attempt_purchase
from tools.reporter import print_run_summary, save_report, save_json_report
from agent.brain import analyze_deal, should_auto_purchase, generate_alert_message

console = Console()


class PriceScoutAgent:
    """
    Autonomous e-commerce price monitoring and deal decision agent.
    """

    def run(self) -> None:
        console.print(Panel.fit(
            f"[bold cyan]🛒 Autonomous Price Scout Agent[/bold cyan]\n"
            f"Mode: {'[yellow]DRY RUN[/yellow]' if EnvConfig.DRY_RUN else '[green]LIVE[/green]'} | "
            f"Auto-purchase: {'[red]ON[/red]' if EnvConfig.AUTO_PURCHASE else '[dim]off[/dim]'} | "
            f"Check interval: {EnvConfig.CHECK_INTERVAL}m",
            border_style="cyan",
        ))

        # ── Step 1: Load watchlist ──────────────────────────────────────
        watchlist = load_watchlist()
        if not watchlist:
            console.print("[yellow]Watchlist is empty. Use --add to add products.[/yellow]")
            return

        console.print(f"\n[bold]Tracking {len(watchlist)} products.[/bold]\n")

        analyses   = []
        alerts_sent = 0
        purchases  = []

        for item in watchlist:
            console.print(f"[bold cyan]{'─'*50}[/bold cyan]")
            console.print(f"[bold]📦 {item.name}[/bold] [dim](id: {item.id})[/dim]")

            # ── Step 2: Scrape prices ───────────────────────────────────
            current_prices = scrape_product_prices(item)

            if not current_prices:
                console.print(f"  [red]✗ Could not scrape any prices.[/red]")
                continue

            # ── Step 3: Update history ──────────────────────────────────
            history = update_price_history(item.id, item.name, current_prices)

            # ── Step 4: Claude analyzes deal ────────────────────────────
            console.print("  [dim]Analyzing deal with Claude...[/dim]")
            analysis = analyze_deal(item, current_prices, history)
            analyses.append(analysis)

            best = analysis.best_deal
            verdict_color = {"buy_now": "green", "wait": "yellow", "skip": "red"}.get(analysis.verdict, "white")
            console.print(
                f"  Score: [{verdict_color}]{analysis.score}/100[/{verdict_color}] | "
                f"Verdict: [{verdict_color}]{analysis.verdict.upper()}[/{verdict_color}] | "
                f"Best: ${best.price:.2f} on {best.platform.title() if best else '?'}"
            )
            console.print(f"  [dim]{analysis.recommendation}[/dim]")

            # ── Step 5: Alert logic ─────────────────────────────────────
            last_alert_price = load_last_alert_price(item.id)
            should_alert, alert_type = should_send_alert(item, analysis, last_alert_price)

            if should_alert:
                msg = generate_alert_message(item, analysis, alert_type)
                send_alert(item, analysis, msg, alert_type)
                alerts_sent += 1
                console.print(f"  [green]🔔 Alert sent ({alert_type})[/green]")

            # ── Step 6: Auto-purchase ───────────────────────────────────
            if should_auto_purchase(item, analysis) and best:
                console.print(f"  [bold yellow]⚡ Auto-purchase triggered![/bold yellow]")
                purchase = attempt_purchase(item, best)
                purchases.append(purchase)
                console.print(
                    f"  Purchase result: [{('green' if purchase.action in ('purchased','cart_added') else 'yellow')}]"
                    f"{purchase.action}[/]"
                )

        # ── Step 7: Report ──────────────────────────────────────────────
        if analyses:
            print_run_summary(analyses)
            save_report(analyses)
            save_json_report(analyses)

        console.print(
            f"[bold green]✓ Run complete.[/bold green] "
            f"{len(analyses)} products analyzed | "
            f"{alerts_sent} alerts sent | "
            f"{len(purchases)} purchase actions"
        )

    def run_continuous(self) -> None:
        """Run on a schedule — checks every CHECK_INTERVAL minutes."""
        import time
        import schedule

        console.print(
            f"[cyan]Continuous mode:[/cyan] checking every {EnvConfig.CHECK_INTERVAL} minutes.\n"
            f"Press Ctrl+C to stop.\n"
        )

        schedule.every(EnvConfig.CHECK_INTERVAL).minutes.do(self.run)
        self.run()  # run immediately on start

        while True:
            schedule.run_pending()
            time.sleep(30)
