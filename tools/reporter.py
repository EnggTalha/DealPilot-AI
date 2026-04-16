"""
tools/reporter.py — Rich terminal report and Markdown/JSON output.
"""

from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from config import DealAnalysis, REPORTS_DIR

console = Console()

VERDICT_COLOR  = {"buy_now": "green", "wait": "yellow", "skip": "red"}
VERDICT_EMOJI  = {"buy_now": "🟢 BUY NOW", "wait": "🟡 WAIT", "skip": "🔴 SKIP"}
TREND_EMOJI    = {"dropping": "📉", "rising": "📈", "stable": "➡️", "volatile": "🌊", "unknown": "❓"}


def print_run_summary(analyses: list[DealAnalysis]) -> None:
    """Print a full terminal summary of all analyzed deals."""
    console.print()
    table = Table(
        title=f"🛒 Price Scout — {len(analyses)} Products Analyzed",
        box=box.ROUNDED, border_style="cyan", show_lines=True,
    )
    table.add_column("Product",    max_width=28)
    table.add_column("Best Price", justify="right", width=11)
    table.add_column("Platform",   width=11)
    table.add_column("Score",      justify="center", width=7)
    table.add_column("Trend",      width=10)
    table.add_column("Verdict",    width=14)

    for a in sorted(analyses, key=lambda x: x.score, reverse=True):
        best  = a.best_deal
        color = VERDICT_COLOR.get(a.verdict, "white")
        trend = TREND_EMOJI.get(a.price_trend, "❓")
        score_color = "green" if a.score >= 75 else "yellow" if a.score >= 50 else "red"

        table.add_row(
            a.product_name[:28],
            f"${best.price:.2f}" if best else "N/A",
            best.platform.title() if best else "—",
            f"[{score_color}]{a.score}[/{score_color}]",
            f"{trend} {a.price_trend}",
            f"[{color}]{VERDICT_EMOJI.get(a.verdict, a.verdict)}[/{color}]",
        )

    console.print(table)

    # Highlight buy_now items
    buys = [a for a in analyses if a.verdict == "buy_now"]
    if buys:
        console.print()
        console.print(Panel(
            "\n".join([
                f"  🛒 [bold]{a.product_name}[/bold] — ${a.best_deal.price:.2f} on {a.best_deal.platform.title()}\n"
                f"     [dim]{a.recommendation}[/dim]"
                for a in buys
            ]),
            title="[bold green]🔥 Buy Now Opportunities[/bold green]",
            border_style="green",
        ))

    console.print()


def save_report(analyses: list[DealAnalysis]) -> Path:
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = REPORTS_DIR / f"report_{ts}.md"

    lines = [
        f"# 🛒 Price Scout Report",
        f"",
        f"**Generated:** {datetime.now().strftime('%B %d, %Y at %H:%M')}  ",
        f"**Products tracked:** {len(analyses)}",
        f"",
        f"---",
        f"",
        f"## 📊 Summary",
        f"",
        f"| Product | Best Price | Platform | Score | Trend | Verdict |",
        f"|---|---|---|---|---|---|",
    ]

    for a in sorted(analyses, key=lambda x: x.score, reverse=True):
        best  = a.best_deal
        trend = TREND_EMOJI.get(a.price_trend, "❓")
        lines.append(
            f"| {a.product_name} | "
            f"{'${:.2f}'.format(best.price) if best else 'N/A'} | "
            f"{best.platform.title() if best else '—'} | "
            f"{a.score}/100 | {trend} {a.price_trend} | "
            f"{VERDICT_EMOJI.get(a.verdict, a.verdict)} |"
        )

    lines += ["", "---", "", "## 🔍 Detailed Analysis", ""]

    for a in analyses:
        best = a.best_deal
        color_md = {"buy_now": "🟢", "wait": "🟡", "skip": "🔴"}
        lines += [
            f"### {color_md.get(a.verdict, '')} {a.product_name}",
            f"",
            f"**Best price:** {'${:.2f} on {}'.format(best.price, best.platform.title()) if best else 'N/A'}  ",
            f"**Deal score:** {a.score}/100  ",
            f"**Price trend:** {TREND_EMOJI.get(a.price_trend, '')} {a.price_trend}  ",
            f"**Verdict:** {VERDICT_EMOJI.get(a.verdict, a.verdict)}",
            f"",
            f"**Analysis:** {a.reasoning}",
            f"",
            f"**Recommendation:** {a.recommendation}",
            f"",
        ]

        if a.current_prices:
            lines += [
                f"| Platform | Price | In Stock | URL |",
                f"|---|---|---|---|",
            ]
            for p in a.current_prices:
                stock = "✓" if p.in_stock else "✗"
                lines.append(f"| {p.platform.title()} | ${p.price:.2f} | {stock} | {p.url[:50]}... |")
            lines.append("")

    out.write_text("\n".join(lines), encoding="utf-8")
    console.print(f"[green]✓[/green] Report saved → {out}")
    return out


def save_json_report(analyses: list[DealAnalysis]) -> Path:
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = REPORTS_DIR / f"report_{ts}.json"
    with open(out, "w") as f:
        json.dump([a.model_dump() for a in analyses], f, indent=2, default=str)
    return out
