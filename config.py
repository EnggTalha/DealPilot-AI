"""
config.py — Central config and data models for the Price Scout Agent.
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).parent
DATA_DIR     = BASE_DIR / "data"
PRODUCTS_DIR = DATA_DIR / "products"
PRICES_DIR   = DATA_DIR / "prices"
ALERTS_DIR   = DATA_DIR / "alerts"
REPORTS_DIR  = DATA_DIR / "reports"
LOG_DIR      = BASE_DIR / "logs"

for d in [PRODUCTS_DIR, PRICES_DIR, ALERTS_DIR, REPORTS_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)


# ── Env ────────────────────────────────────────────────────────────────
class EnvConfig:
    ANTHROPIC_API_KEY:      str  = os.getenv("ANTHROPIC_API_KEY", "")
    TELEGRAM_BOT_TOKEN:     str  = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID:       str  = os.getenv("TELEGRAM_CHAT_ID", "")
    ALERT_EMAIL_FROM:       str  = os.getenv("ALERT_EMAIL_FROM", "")
    ALERT_EMAIL_TO:         str  = os.getenv("ALERT_EMAIL_TO", "")
    ALERT_EMAIL_PASSWORD:   str  = os.getenv("ALERT_EMAIL_PASSWORD", "")
    DRY_RUN:               bool  = os.getenv("DRY_RUN", "true").lower() == "true"
    CHECK_INTERVAL:         int  = int(os.getenv("CHECK_INTERVAL_MINUTES", "60"))
    TIMEZONE:               str  = os.getenv("TIMEZONE", "Asia/Karachi")
    CURRENCY:               str  = os.getenv("CURRENCY", "USD")
    AUTO_PURCHASE:         bool  = os.getenv("AUTO_PURCHASE", "false").lower() == "true"
    MAX_AUTO_PURCHASE:    float  = float(os.getenv("MAX_AUTO_PURCHASE_USD", "50"))
    DROP_THRESHOLD:        float = float(os.getenv("DEFAULT_DROP_THRESHOLD", "10"))
    DEFAULT_MAX_PRICE:    float  = float(os.getenv("DEFAULT_MAX_PRICE", "500"))


# ── Data Models ────────────────────────────────────────────────────────

class WatchlistItem(BaseModel):
    id:               str
    name:             str
    urls:             List[str]             # one URL per platform to check
    target_price:     Optional[float] = None   # alert if price drops to/below this
    drop_threshold:   float = 10.0             # alert if drops by X% from last seen
    max_price:        Optional[float] = None   # never buy above this
    priority:         str = "normal"           # low | normal | high | urgent
    notes:            Optional[str] = None
    auto_buy:         bool = False             # override global AUTO_PURCHASE
    tags:             List[str] = Field(default_factory=list)


class PricePoint(BaseModel):
    product_id:   str
    platform:     str       # "amazon" | "ebay" | "aliexpress" | "daraz" | "local"
    url:          str
    price:        float
    currency:     str = "USD"
    in_stock:     bool = True
    seller:       str = ""
    rating:       Optional[float] = None
    review_count: Optional[int] = None
    scraped_at:   str
    title:        str = ""
    image_url:    str = ""


class PriceHistory(BaseModel):
    product_id:   str
    product_name: str
    history:      List[PricePoint] = Field(default_factory=list)
    lowest_ever:  Optional[float] = None
    highest_ever: Optional[float] = None
    avg_price:    Optional[float] = None


class DealAnalysis(BaseModel):
    product_id:     str
    product_name:   str
    current_prices: List[PricePoint]
    best_deal:      Optional[PricePoint] = None
    verdict:        str        # "buy_now" | "wait" | "skip" | "alert_sent"
    score:          int        # 0–100 deal quality score
    reasoning:      str
    price_trend:    str        # "dropping" | "rising" | "stable" | "volatile"
    recommendation: str        # plain English recommendation
    savings:        float = 0.0   # how much saved vs avg/highest
    alert_worthy:   bool = False


class PurchaseAction(BaseModel):
    product_id:   str
    product_name: str
    platform:     str
    url:          str
    price:        float
    action:       str          # "purchased" | "cart_added" | "dry_run" | "skipped"
    reason:       str
    timestamp:    str


class AlertRecord(BaseModel):
    product_id:   str
    product_name: str
    alert_type:   str          # "price_drop" | "target_hit" | "back_in_stock" | "deal"
    message:      str
    price:        float
    platform:     str
    url:          str
    sent_at:      str
    channels:     List[str]    # ["telegram", "email"]


# ── Supported platforms ────────────────────────────────────────────────
PLATFORM_SELECTORS = {
    "amazon": {
        "price":    ["#priceblock_ourprice", "#priceblock_dealprice", ".a-price .a-offscreen", "#corePrice_feature_div .a-offscreen"],
        "title":    ["#productTitle"],
        "stock":    ["#availability span"],
        "rating":   [".a-icon-alt"],
        "reviews":  ["#acrCustomerReviewText"],
    },
    "ebay": {
        "price":    [".x-price-primary .ux-textspans", ".x-bin-price__content .ux-textspans"],
        "title":    [".x-item-title__mainTitle span"],
        "stock":    [".d-quantity__availability"],
    },
    "aliexpress": {
        "price":    [".product-price-current", ".uniform-banner-box-price"],
        "title":    [".product-title-text"],
    },
}
