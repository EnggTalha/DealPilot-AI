# 🛒 Autonomous E-commerce Price Scout Agent

> Give it a product list and a budget. The agent continuously monitors prices across Amazon, eBay, and AliExpress — detects drops, scores deals with Claude, alerts you via Telegram, and optionally auto-purchases when your criteria are met.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![Claude](https://img.shields.io/badge/Powered%20by-Claude%20Opus-blueviolet?logo=anthropic)
![Telegram](https://img.shields.io/badge/Alerts-Telegram-blue?logo=telegram)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)

---

## 📸 Demo

```
╭─────────────────────────────────────────────────────────────╮
│  🛒 Autonomous Price Scout Agent                            │
│  Mode: DRY RUN | Auto-purchase: off | Check interval: 60m  │
╰─────────────────────────────────────────────────────────────╯

Tracking 3 products.

──────────────────────────────────────────────────────────────
📦 Sony WH-1000XM5 Headphones (id: demo001)
  Scraping amazon: https://amazon.com/dp/B09XS7JWHH...
  Scraping ebay: https://ebay.com/itm/sony-wh1000xm5...
  Analyzing deal with Claude...
  Score: 84/100 | Verdict: BUY NOW | Best: $289.99 on Ebay
  eBay has it $20 below the 90-day average. Buy now.
  🔔 Alert sent (price_drop)

──────────────────────────────────────────────────────────────
📦 iPhone 15 Pro 256GB (id: demo002)
  Scraping amazon: https://amazon.com/dp/B0CHX2F5QT...
  Analyzing deal with Claude...
  Score: 52/100 | Verdict: WAIT | Best: $949.00 on Amazon
  Price is $49 above the target. Historical data shows drops in Nov/Dec.

──────────────────────────────────────────────────────────────
📦 Logitech MX Master 3S Mouse (id: demo003)
  Scraping amazon: https://amazon.com/dp/B09HM94VDS...
  Scraping bestbuy...
  Analyzing deal with Claude...
  Score: 91/100 | Verdict: BUY NOW | Best: $79.99 on Bestbuy
  $79.99 is below your $80 target. Auto-buy triggered!
  ⚡ Auto-purchase triggered!
  Purchase result: dry_run

┌──────────────────────────────┬────────────┬──────────┬───────┬──────────┬───────────────┐
│ Product                      │ Best Price │ Platform │ Score │ Trend    │ Verdict       │
├──────────────────────────────┼────────────┼──────────┼───────┼──────────┼───────────────┤
│ Logitech MX Master 3S Mouse  │  $79.99    │ Bestbuy  │  91   │ 📉 drop  │ 🟢 BUY NOW   │
│ Sony WH-1000XM5 Headphones   │ $289.99    │ Ebay     │  84   │ 📉 drop  │ 🟢 BUY NOW   │
│ iPhone 15 Pro 256GB          │ $949.00    │ Amazon   │  52   │ ➡️ stable │ 🟡 WAIT      │
└──────────────────────────────┴────────────┴──────────┴───────┴──────────┴───────────────┘

🔥 Buy Now Opportunities
  🛒 Logitech MX Master 3S Mouse — $79.99 on Bestbuy
     Below your $80 target. Great time to buy.
  🛒 Sony WH-1000XM5 Headphones — $289.99 on eBay
     $20 below 90-day average. Buy now.

✓ Run complete. 3 products analyzed | 1 alert sent | 1 purchase action
```

**Telegram alert received:**
```
📉 Price Alert: Sony WH-1000XM5 Headphones

💵 Current best: $289.99 on Ebay
📊 Deal score: 84/100
💰 Savings: ~$20.00 vs average
📈 Trend: Dropping

🤖 Claude says: eBay has this $20 below the 90-day average — buy now before it rebounds.

🔗 https://ebay.com/itm/sony-wh1000xm5
```

---

## 🧠 How It Works

```
┌──────────────┐   ┌──────────────┐   ┌──────────────────────────┐
│  1. WATCHLIST│──▶│  2. SCRAPE   │──▶│  3. ANALYZE (Claude)     │
│              │   │              │   │                          │
│  JSON file   │   │  Playwright  │   │  Price vs history        │
│  Products +  │   │  Amazon      │   │  Deal score 0-100        │
│  criteria    │   │  eBay        │   │  buy_now/wait/skip       │
│  target $    │   │  AliExpress  │   │  Price trend detection   │
└──────────────┘   └──────────────┘   └──────────────────────────┘
                                                  │
                                                  ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────────────────┐
│  6. REPORT   │◀──│  5. PURCHASE │◀──│  4. ALERT                │
│              │   │              │   │                          │
│  Markdown    │   │  Playwright  │   │  Telegram instant push   │
│  JSON        │   │  Amazon      │   │  Email SMTP              │
│  Terminal    │   │  1-Click/Cart│   │  Anti-spam logic         │
│  table       │   │  (opt-in)    │   │  Drop threshold filter   │
└──────────────┘   └──────────────┘   └──────────────────────────┘
```

### Agent Decision Logic

```
Scrape prices
     │
     ▼
Update price history
     │
     ▼
Claude scores deal (0-100)
     │
     ├── Score ≥ 80 + meets criteria ──▶ verdict: buy_now
     ├── Price dropping, not at target ──▶ verdict: wait
     └── Poor value / far from target ──▶ verdict: skip
     │
     ▼
Should we alert?
     ├── target_price hit → YES (target_hit alert)
     ├── dropped ≥ threshold% since last alert → YES (price_drop alert)
     ├── score ≥ 80 + first time → YES (deal alert)
     └── none of above → NO (prevent spam)
     │
     ▼
Should we auto-purchase?
     ├── AUTO_PURCHASE=true AND item.auto_buy=true
     ├── verdict = buy_now AND score ≥ 75
     ├── price ≤ MAX_AUTO_PURCHASE_USD
     └── price ≤ item.max_price
```

---

## ✨ Features

| Feature | Details |
|---|---|
| 🔍 Multi-platform scraping | Amazon, eBay, AliExpress, Walmart, BestBuy via Playwright |
| 🧠 Claude deal scoring | AI scores each deal 0–100 and gives buy/wait/skip verdict |
| 📊 Price history | Tracks lowest/highest/average price over time |
| 📉 Drop detection | Alerts only when price drops by your configured threshold |
| 📱 Telegram alerts | Instant push notifications with deal details |
| 📧 Email alerts | Optional fallback via Gmail SMTP |
| 🛒 Auto-purchase | Optional Amazon 1-Click / Add-to-Cart automation |
| 🔁 Anti-spam | Won't re-alert unless price drops another X% |
| ⏱️ Continuous mode | Checks every N minutes in the background |
| 📄 Reports | Full Markdown + JSON deal reports saved locally |

---

## 🗂️ Project Structure

```
price-scout/
├── main.py                      # CLI entry point
├── config.py                    # Config, env vars, Pydantic models
├── requirements.txt
├── .env.example
│
├── agent/
│   ├── brain.py                 # Claude: deal analysis + purchase decisions
│   └── orchestrator.py          # Main agentic loop
│
├── tools/
│   ├── watchlist.py             # Product watchlist CRUD
│   ├── scraper.py               # Playwright + BS4 price scraper
│   ├── alerter.py               # Telegram + email alert delivery
│   ├── purchaser.py             # Amazon auto-purchase via Playwright
│   └── reporter.py              # Terminal + Markdown report generator
│
└── data/
    ├── products/watchlist.json  # Your product watchlist
    ├── prices/<id>.json         # Per-product price history
    ├── alerts/alert_log.json    # Alert history (prevents spam)
    └── reports/                 # Deal reports
```

---

## 🚀 Quickstart

### 1. Clone & install

```bash
git clone https://github.com/yourusername/price-scout-agent.git
cd price-scout-agent

python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

pip install -r requirements.txt
playwright install chromium    # install headless browser
```

### 2. Configure

```bash
cp .env.example .env
# Add ANTHROPIC_API_KEY at minimum
```

### 3. Set up Telegram alerts (free, 2 minutes)

1. Message **@BotFather** on Telegram → `/newbot` → copy the token
2. Start your bot (message it once)
3. Get your chat ID: visit `https://api.telegram.org/bot<TOKEN>/getUpdates`
4. Add to `.env`:
   ```
   TELEGRAM_BOT_TOKEN=your_token
   TELEGRAM_CHAT_ID=your_chat_id
   ```

### 4. Add your first product

```bash
python main.py --add
# Interactive prompts: name, URL(s), target price, drop threshold
```

### 5. Run dry-run (safe — no alerts sent)

```bash
python main.py --dry-run
```

### 6. Go live

```bash
python main.py --live
```

### 7. Run continuously (check every hour)

```bash
python main.py --watch --live
```

---

## ⚙️ CLI Reference

```
python main.py [OPTIONS]

Options:
  --watch           Run continuously (check every CHECK_INTERVAL minutes)
  --add             Interactively add a product to your watchlist
  --list            Show all products in your watchlist
  --remove ID       Remove a product from the watchlist
  --dry-run         Simulate — no real alerts or purchases
  --live            Real alerts + purchases
  --interval INT    Check interval in minutes (overrides .env)

Examples:
  python main.py --list                     # see watchlist
  python main.py --add                      # add a product
  python main.py --dry-run                  # safe test run
  python main.py --watch --live             # continuous monitoring
  python main.py --remove demo001           # remove product
```

---

## 🔧 Watchlist Configuration

Each product in your watchlist supports:

```json
{
  "id": "abc123",
  "name": "Sony WH-1000XM5",
  "urls": [
    "https://amazon.com/dp/B09XS7JWHH",
    "https://ebay.com/itm/123456"
  ],
  "target_price": 280.0,
  "drop_threshold": 10.0,
  "max_price": 350.0,
  "priority": "high",
  "auto_buy": false,
  "notes": "Been watching for months",
  "tags": ["audio", "electronics"]
}
```

---

## ⚠️ Auto-Purchase Safety

Auto-purchasing is **disabled by default**. To enable it safely:

1. Set `AUTO_PURCHASE=true` in `.env`
2. Set `MAX_AUTO_PURCHASE_USD=50` (hard ceiling — never buys above this)
3. Set `auto_buy: true` on specific watchlist items
4. Claude must give the deal a score of 75+ before purchasing

Supported platforms for auto-purchase: **Amazon** (via saved browser session)

---

## 🔑 API Keys & Cost

| Service | Used For | Cost |
|---|---|---|
| Anthropic Claude | Deal analysis + decisions | ~$0.02–0.05 per product per run |
| Playwright | Price scraping | Free |
| Telegram Bot API | Push alerts | Free |
| Gmail SMTP | Email alerts | Free |

**Estimated cost per run (10 products):** ~$0.20–0.50

---

## 🤝 Contributing

Ideas welcome:

- [ ] Daraz.pk support (Pakistan)
- [ ] Camelcamelcamel integration (Amazon price history API)
- [ ] Price chart visualization (matplotlib / plotly)
- [ ] WhatsApp alerts via Twilio
- [ ] Discord webhook support
- [ ] Browser extension to add products from any page

---

## 📄 License

MIT — see [LICENSE](LICENSE)

---

## 🙋 Author

Built by [EnggTalha](https://github.com/EnggTalha)

> ⭐ Star this repo if it saved you money!
