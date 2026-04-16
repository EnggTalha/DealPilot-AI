"""
agent/brain.py — Claude-powered deal analysis and purchase decision engine.
Analyzes price history, trends, and context to decide: buy now / wait / skip.
"""

from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import List, Optional
import anthropic
from rich.console import Console

from config import (
    EnvConfig, WatchlistItem, PricePoint, PriceHistory,
    DealAnalysis, AlertRecord
)

console = Console()
_client: Optional[anthropic.Anthropic] = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=EnvConfig.ANTHROPIC_API_KEY)
    return _client


# ── Deal analysis ──────────────────────────────────────────────────────

def analyze_deal(
    item: WatchlistItem,
    current_prices: List[PricePoint],
    history: PriceHistory,
) -> DealAnalysis:
    """
    Claude analyzes prices against history and user criteria to decide:
    buy_now | wait | skip | alert_sent
    """
    if not current_prices:
        return DealAnalysis(
            product_id=item.id,
            product_name=item.name,
            current_prices=[],
            verdict="skip",
            score=0,
            reasoning="No prices could be scraped.",
            price_trend="unknown",
            recommendation="Check product URLs — scraping returned no data.",
        )

    best = min(current_prices, key=lambda p: p.price)
    in_stock_prices = [p for p in current_prices if p.in_stock]
    best_in_stock = min(in_stock_prices, key=lambda p: p.price) if in_stock_prices else best

    # Build price history summary
    recent = history.history[-10:] if history.history else []
    history_summary = "No history yet." if not recent else "\n".join([
        f"- {p.scraped_at[:10]} | {p.platform}: ${p.price:.2f} | {'in stock' if p.in_stock else 'out of stock'}"
        for p in recent
    ])

    platform_prices = "\n".join([
        f"- {p.platform}: ${p.price:.2f} | {'✓ In Stock' if p.in_stock else '✗ Out of Stock'} | {p.url[:60]}"
        for p in current_prices
    ])

    prompt = f"""You are an expert deal analyst and personal finance advisor. Analyze this product deal.

PRODUCT: {item.name}
User notes: {item.notes or 'none'}
Priority: {item.priority}

USER CRITERIA:
- Target price: ${item.target_price:.2f if item.target_price else 'not set'}
- Max willing to pay: ${item.max_price:.2f if item.max_price else 'not set'}
- Alert if price drops by: {item.drop_threshold}%

CURRENT PRICES (just scraped):
{platform_prices}

PRICE HISTORY (last 10 data points):
{history_summary}

ALL-TIME STATS:
- Lowest ever: ${history.lowest_ever:.2f if history.lowest_ever else 'unknown'}
- Highest ever: ${history.highest_ever:.2f if history.highest_ever else 'unknown'}
- Average price: ${history.avg_price:.2f if history.avg_price else 'unknown'}

Respond ONLY with JSON (no markdown):
{{
  "verdict": "buy_now|wait|skip",
  "score": <integer 0-100, 100=unmissable deal>,
  "price_trend": "dropping|rising|stable|volatile",
  "reasoning": "2-3 sentences of analysis with specific numbers",
  "recommendation": "Clear 1-sentence plain English action",
  "alert_worthy": <true if user should be notified immediately>,
  "savings": <float, how much saved vs average/highest, 0 if none>
}}

Verdict guide:
- buy_now: price is at or near lowest, meets criteria, good deal
- wait: price is dropping or likely to drop, not urgent
- skip: poor value, better alternatives exist, or price won't meet criteria
- score 90+: exceptional deal, rare opportunity
- score 70-89: good deal, worth buying
- score 50-69: decent deal, could be better
- score <50: wait or skip"""

    try:
        resp = get_client().messages.create(
            model="claude-opus-4-5",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip().replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)

        return DealAnalysis(
            product_id=item.id,
            product_name=item.name,
            current_prices=current_prices,
            best_deal=best_in_stock,
            verdict=data["verdict"],
            score=data["score"],
            reasoning=data["reasoning"],
            price_trend=data["price_trend"],
            recommendation=data["recommendation"],
            savings=data.get("savings", 0.0),
            alert_worthy=data.get("alert_worthy", False),
        )

    except Exception as e:
        console.print(f"  [red]Deal analysis failed:[/red] {e}")
        return DealAnalysis(
            product_id=item.id,
            product_name=item.name,
            current_prices=current_prices,
            best_deal=best_in_stock,
            verdict="wait",
            score=50,
            reasoning=f"Analysis error: {e}",
            price_trend="unknown",
            recommendation="Manual review needed.",
        )


# ── Purchase decision ──────────────────────────────────────────────────

def should_auto_purchase(item: WatchlistItem, analysis: DealAnalysis) -> bool:
    """
    Decide whether to auto-purchase based on agent config + deal analysis.
    Multiple safety checks to prevent accidental purchases.
    """
    if not EnvConfig.AUTO_PURCHASE:
        return False
    if not item.auto_buy:
        return False
    if analysis.verdict != "buy_now":
        return False
    if analysis.score < 75:
        return False
    if not analysis.best_deal:
        return False
    if analysis.best_deal.price > EnvConfig.MAX_AUTO_PURCHASE:
        return False
    if item.max_price and analysis.best_deal.price > item.max_price:
        return False
    return True


# ── Alert generation ───────────────────────────────────────────────────

def generate_alert_message(
    item: WatchlistItem,
    analysis: DealAnalysis,
    alert_type: str,
) -> str:
    """Generate a clear, actionable alert message."""
    best = analysis.best_deal
    if not best:
        return f"🔔 {item.name} — price update available."

    emoji_map = {
        "price_drop":     "📉",
        "target_hit":     "🎯",
        "back_in_stock":  "✅",
        "deal":           "🔥",
    }
    emoji = emoji_map.get(alert_type, "🔔")

    savings_text = f"\n💰 Savings: ~${analysis.savings:.2f} vs average" if analysis.savings > 0 else ""

    return (
        f"{emoji} *Price Alert: {item.name}*\n\n"
        f"💵 Current best: *${best.price:.2f}* on {best.platform.title()}\n"
        f"📊 Deal score: {analysis.score}/100{savings_text}\n"
        f"📈 Trend: {analysis.price_trend.title()}\n\n"
        f"🤖 Claude says: _{analysis.recommendation}_\n\n"
        f"🔗 {best.url}"
    )
