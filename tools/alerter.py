"""
tools/alerter.py — Deliver price alerts via Telegram and/or email.
Telegram is recommended — free, instant, no setup beyond a bot token.
"""

from __future__ import annotations
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List
from rich.console import Console

from config import EnvConfig, AlertRecord, DealAnalysis, WatchlistItem, ALERTS_DIR
import json

console = Console()


def send_alert(
    item: WatchlistItem,
    analysis: DealAnalysis,
    message: str,
    alert_type: str,
) -> AlertRecord:
    """Send alert via all configured channels."""
    channels = []
    best = analysis.best_deal

    if EnvConfig.DRY_RUN:
        console.print(f"\n[yellow][DRY RUN] Alert for {item.name}:[/yellow]")
        console.print(message)
        channels = ["dry_run"]
    else:
        if EnvConfig.TELEGRAM_BOT_TOKEN and EnvConfig.TELEGRAM_CHAT_ID:
            ok = _send_telegram(message)
            if ok:
                channels.append("telegram")

        if EnvConfig.ALERT_EMAIL_FROM and EnvConfig.ALERT_EMAIL_TO:
            ok = _send_email(
                subject=f"🔔 Price Alert: {item.name} — ${best.price:.2f if best else '?'} on {best.platform.title() if best else '?'}",
                body=message,
            )
            if ok:
                channels.append("email")

        if not channels:
            console.print(f"[yellow]No alert channels configured. Alert printed to terminal.[/yellow]")
            console.print(message)
            channels = ["terminal"]

    record = AlertRecord(
        product_id=item.id,
        product_name=item.name,
        alert_type=alert_type,
        message=message,
        price=best.price if best else 0,
        platform=best.platform if best else "unknown",
        url=best.url if best else "",
        sent_at=datetime.now(timezone.utc).isoformat(),
        channels=channels,
    )

    _save_alert_record(record)
    return record


def _send_telegram(message: str) -> bool:
    """Send message via Telegram Bot API."""
    try:
        import requests
        url = f"https://api.telegram.org/bot{EnvConfig.TELEGRAM_BOT_TOKEN}/sendMessage"
        resp = requests.post(url, json={
            "chat_id": EnvConfig.TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False,
        }, timeout=10)
        if resp.status_code == 200:
            console.print(f"  [green]✓[/green] Telegram alert sent.")
            return True
        else:
            console.print(f"  [red]Telegram error {resp.status_code}:[/red] {resp.text[:100]}")
            return False
    except Exception as e:
        console.print(f"  [red]Telegram failed:[/red] {e}")
        return False


def _send_email(subject: str, body: str) -> bool:
    """Send alert via Gmail SMTP."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = EnvConfig.ALERT_EMAIL_FROM
        msg["To"]      = EnvConfig.ALERT_EMAIL_TO

        # Plain text version
        text_part = MIMEText(body.replace("*", "").replace("_", ""), "plain")

        # HTML version
        html_body = body.replace("\n", "<br>").replace("*", "<b>").replace("_", "<i>")
        html_part = MIMEText(f"<html><body>{html_body}</body></html>", "html")

        msg.attach(text_part)
        msg.attach(html_part)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EnvConfig.ALERT_EMAIL_FROM, EnvConfig.ALERT_EMAIL_PASSWORD)
            server.sendmail(EnvConfig.ALERT_EMAIL_FROM, EnvConfig.ALERT_EMAIL_TO, msg.as_string())

        console.print(f"  [green]✓[/green] Email alert sent to {EnvConfig.ALERT_EMAIL_TO}")
        return True
    except Exception as e:
        console.print(f"  [red]Email failed:[/red] {e}")
        return False


def _save_alert_record(record: AlertRecord) -> None:
    path = ALERTS_DIR / "alert_log.json"
    existing = []
    if path.exists():
        try:
            with open(path) as f:
                existing = json.load(f)
        except Exception:
            pass
    existing.append(record.model_dump())
    with open(path, "w") as f:
        json.dump(existing, f, indent=2, default=str)


def should_send_alert(
    item: WatchlistItem,
    analysis: DealAnalysis,
    last_alert_price: float = None,
) -> tuple[bool, str]:
    """
    Decide whether to send an alert and what type.
    Returns (should_alert, alert_type).
    Prevents alert spam by checking against last alert price.
    """
    if not analysis.best_deal:
        return False, ""

    current_price = analysis.best_deal.price

    # Target price hit
    if item.target_price and current_price <= item.target_price:
        return True, "target_hit"

    # Significant drop from last alert
    if last_alert_price and last_alert_price > 0:
        drop_pct = (last_alert_price - current_price) / last_alert_price * 100
        if drop_pct >= item.drop_threshold:
            return True, "price_drop"
        return False, ""   # not enough of a drop to re-alert

    # No previous alert — alert if score is high enough
    if analysis.score >= 80 and analysis.alert_worthy:
        return True, "deal"

    return False, ""


def load_last_alert_price(product_id: str) -> float:
    """Get the price at which we last sent an alert for this product."""
    path = ALERTS_DIR / "alert_log.json"
    if not path.exists():
        return 0.0
    try:
        with open(path) as f:
            records = json.load(f)
        product_alerts = [r for r in records if r["product_id"] == product_id]
        if product_alerts:
            return product_alerts[-1]["price"]
    except Exception:
        pass
    return 0.0
