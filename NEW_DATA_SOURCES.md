# New Data Sources for Stradegy Bot — Complete Research

## Executive Summary

**Current sources:** Reddit, Discord, StockTwits, SEC EDGAR, Finnhub News, OpenInsider, Google Trends, Technical Indicators, Earnings (Finnhub)

**Found:** 34 new viable sources across 9 categories

**Quick wins (free, <1 hour each):** Alpaca News, yfinance Options, FINRA Short Interest, FRED Macro, FearGreedChart, HackerNews

---

## Category 1: Social Sentiment (Beyond Reddit/Discord)

### 1. ⭐ Telegram API (FREE — Best Value)
- **URL:** https://core.telegram.org/api / https://docs.telethon.dev
- **Cost:** COMPLETELY FREE
- **Auth:** api_id + api_hash from https://my.telegram.org (free, instant)
- **Data:** Stock channel messages, reactions (sentiment proxy), views, forwards
- **Integration:** `pip install telethon`
- **Rate Limits:** No hard limits. FloodWaitError after ~30 req/sec — sleep and retry
- **Code:**
```python
from telethon import TelegramClient
async def scan():
    client = TelegramClient("session", api_id, api_hash)
    await client.start()
    async for msg in client.iter_messages("stock_signals_channel", limit=50):
        reactions = msg.reactions.results if msg.reactions else []
        sentiment = sum(r.count for r in reactions if str(r.reaction) in ["👍","🔥","🚀"])
```
- **Noise:** LOW-MEDIUM. Well-moderated trading channels have high signal
- **Difficulty:** 2/5

### 2. ⭐ Bluesky AT Protocol (FREE — Best New Source)
- **URL:** https://docs.bsky.app/docs/api/at-protocol-xrpc-api
- **Cost:** COMPLETELY FREE. Open protocol
- **Auth:** Optional for public data. App password for posting
- **Data:** Finance community posts, cashtags ($AAPL), engagement metrics
- **Integration:** `pip install atproto`
- **Rate Limits:** Generous. Firehose available via WebSocket
- **Code:**
```python
from atproto import Client
client = Client()
resp = client.app.bsky.feed.search_posts({"q": "$AAPL", "limit": 50})
for post in resp.posts:
    engagement = post.like_count + post.repost_count * 2 + post.reply_count
```
- **Noise:** LOW. Growing finance community, less bot spam than Twitter/X
- **Difficulty:** 2/5

### 3. ⭐ HackerNews Algolia API (FREE)
- **URL:** https://hn.algolia.com/api
- **Cost:** COMPLETELY FREE. No auth, no API key
- **Data:** Tech stock discussions, sentiment proxy via points/comments
- **Integration:** REST API
- **Rate Limits:** ~10,000 requests/hour
- **Code:**
```python
import requests
resp = requests.get("http://hn.algolia.com/api/v1/search", params={"query": "AAPL", "tags": "story"})
```
- **Noise:** LOW-MEDIUM. High-quality discussions. Tech stocks dominate
- **Difficulty:** 1/5

### 4. YouTube Data API v3 (FREE)
- **URL:** https://developers.google.com/youtube/v3
- **Cost:** 10,000 quota units/day FREE
- **Auth:** Google Cloud Project + API Key
- **Data:** Stock video comments, sentiment via likes/replies
- **Integration:** googleapiclient
- **Rate Limits:** 10K quota/day. commentThreads.list = 1 unit/call
- **Code:**
```python
from googleapiclient.discovery import build
youtube = build("youtube", "v3", developerKey=API_KEY)
comments = youtube.commentThreads().list(part="snippet", videoId=VIDEO_ID, maxResults=100)
```
- **Noise:** MEDIUM. Filter by searchTerms ("buy", "sell", "bullish", "bearish")
- **Difficulty:** 2/5

### 5. X/Twitter API v2
- **URL:** https://docs.x.com/x-api
- **Cost:** $200-$5000/mo. Free tier gutted (1 request/15min)
- **Auth:** OAuth 2.0 Bearer Token
- **Data:** Stock mentions, sentiment, trending tickers
- **Rate Limits:** 450 req/15min (Basic), 900/15min (Pro $5000/mo)
- **Noise:** MEDIUM-HIGH. Lots of bot/spam accounts
- **Difficulty:** 3/5
- **Verdict:** Skip unless you have budget. Bluesky + Telegram are better free alternatives

### 6. Adanos Finance Sentiment API
- **URL:** https://api.adanos.org / pip install `social-stock-sentiment`
- **Cost:** Free tier: 250 requests/month
- **Data:** Reddit, X/Twitter, News, Polymarket sentiment aggregated
- **Integration:** Python SDK with async support
- **Code:**
```python
from adanos import Stock
client = Stock(api_key="YOUR_KEY")
reddit_trending = client.reddit.trending(days=7, limit=20)
x_trending = client.x.trending(days=1, limit=20)
```
- **Difficulty:** 1/5 - One SDK covers 4 sources
- **Noise:** LOW. Aggregated and cleaned

### 7. TradingView Community (Scraping)
- **URL:** https://www.tradingview.com/ideas/
- **Cost:** Free (scraping)
- **Data:** Technical analysis ideas, sentiment, price predictions
- **Integration:** BeautifulSoup scraping
- **Difficulty:** 3/5

### 8. Mastodon / ActivityPub
- **URL:** https://docs.joinmastodon.org/methods/timelines/
- **Cost:** FREE
- **Data:** Hashtag-based stock discussions
- **Integration:** REST API
- **Difficulty:** 3/5. Instance fragmentation means querying multiple servers
- **Noise:** MEDIUM-HIGH

### 9. SeekingAlpha / Motley Fool (Scraping/RSS)
- **URL:** https://seekingalpha.com/
- **Cost:** Free (limited articles)
- **Data:** Analyst articles, earnings previews, sentiment
- **Integration:** RSS feeds + scraping
- **Difficulty:** 3/5

### 10. InvestorsHub / Stockhouse (Scraping)
- **URL:** https://investorshub.advfn.com/
- **Cost:** Free (scraping)
- **Data:** Message board discussions
- **Noise:** HIGH. Notorious for pump-and-dump schemes
- **Difficulty:** 3/5
- **Verdict:** LOW PRIORITY

---

## Category 2: Options Flow & Unusual Activity

### 11. ⭐ yfinance Options (FREE — Already Installed)
- **URL:** https://github.com/ranaroussi/yfinance
- **Cost:** FREE (already in requirements)
- **Data:** Options chains with volume, OI, implied vol
- **Integration:** Already installed! Just use it
- **Code:**
```python
import yfinance as yf
ticker = yf.Ticker("AAPL")
chain = ticker.option_chain("2025-06-20")
calls = chain.calls  # DataFrame with volume, openInterest
# Detect unusual: volume/OI > 3x
```
- **Difficulty:** 1/5
- **Note:** Rate limited by Yahoo, use with delays

### 12. ⭐ Tradier API — Free Options Chain (FREE)
- **URL:** https://developer.tradier.com/
- **Cost:** FREE sandbox with delayed data (15 min delay)
- **Data:** Options chains with volume, open interest, Greeks
- **Integration:** REST API, 120 requests/min
- **Code:**
```python
import requests
headers = {"Authorization": "Bearer TOKEN", "Accept": "application/json"}
url = "https://sandbox.tradier.com/v1/markets/options/chains"
params = {"symbol": "AAPL", "expiration": "2025-06-20"}
resp = requests.get(url, headers=headers, params=params)
```
- **Difficulty:** 2/5

### 13. Mboum API — Unusual Options Activity
- **URL:** https://mboum.com/pages/api
- **Cost:** Free tier available
- **Data:** Pre-filtered unusual options activity (Vol/OI ratio > 3x)
- **Integration:** REST API
- **Code:**
```python
url = "https://api.mboum.com/v1/markets/options/unusual-options-activity"
headers = {"Authorization": "Bearer API_KEY"}
params = {"type": "STOCKS", "page": "1"}
```
- **Difficulty:** 2/5

### 14. OptionWhales — AI-Powered Options Flow
- **URL:** https://api.optionwhales.io/v1/
- **Cost:** FREE (top 3 tickers only). PRO: $19/mo
- **Data:** AI-scored directional flow, GEX, strategy clustering
- **Integration:** REST API + WebSocket
- **Endpoints:**
```
GET /v1/flow/current — Current session intent rankings
GET /v1/abnormal-trades/current — Abnormal trades
WS  /v1/ws/abnormal-trades — Real-time stream (Pro)
```
- **Rate Limits:** 10/min (free), 60/min (pro)
- **Difficulty:** 2/5

### 15. Quant Data — Exchange-Licensed Options + Dark Pool
- **URL:** https://quantdata.us/api
- **Cost:** $149.99/mo. 7-day free trial
- **Data:** Options order flow, net delta exposure, dark pool prints, dealer gamma
- **Integration:** REST JSON with MCP support
- **Rate Limits:** 240 requests/min
- **Difficulty:** 3/5

### 16. CBOE VIX & Options Data
- **URL:** https://www.cboe.com/tradable_products/vix/
- **Cost:** Free
- **Data:** VIX term structure, options volume by strike
- **Integration:** Direct CSV download
- **Difficulty:** 2/5

### 17. Webull OpenAPI (Unofficial)
- **URL:** https://github.com/tedchou12/webull
- **Cost:** Free (unofficial, use at own risk)
- **Data:** Real-time quotes, options flow, analyst ratings
- **Integration:** Python SDK (unofficial)
- **Difficulty:** 3/5

---

## Category 3: Short Interest & Institutional Data

### 18. ⭐ FINRA API — Short Interest + Daily Short Sale (FREE)
- **URL:** https://api.finra.org/data/group/otcMarket/name/EquityShortInterest
- **Cost:** COMPLETELY FREE
- **Auth:** None required
- **Data:** Bimonthly short interest, daily Reg SHO short sale volume
- **Integration:** REST API (POST with JSON filters)
- **Code:**
```python
import requests
url = "https://api.finra.org/data/group/otcMarket/name/EquityShortInterest"
body = {"compareFilters": [{"compareType": "EQUAL", "fieldName": "settlementDate", "fieldValue": "2025-05-15"}], "limit": 5000}
resp = requests.post(url, json=body)
```
- **Difficulty:** 2/5
- **Why Stradegy needs it:** Direct from regulator. Twice-monthly + daily data

### 19. QuiverQuant — Congress + Insider + Dark Pool
- **URL:** https://api.quiverquant.com
- **Cost:** Free tier: 100 requests/day. Hobbyist $30/mo
- **Data:** Congressional trades, insider trading, institutional holdings, lobbying
- **Integration:** REST API with Bearer token
- **Code:**
```python
import requests
headers = {"Authorization": "Bearer TOKEN"}
resp = requests.get("https://api.quiverquant.com/beta/live/congresstrading", headers=headers)
```
- **Difficulty:** 2/5

### 20. KeyVex — Dark Pool ATS + Congress + Insider + 13F
- **URL:** https://mcp.keyvex.com
- **Cost:** FREE: 5,000 calls/month. Builder $29/mo
- **Data:** 38 tools including OTC dark-pool volume, congressional trades, insider transactions, institutional holdings, SEC fails-to-deliver
- **Integration:** MCP (JSON-RPC) with REST fallback
- **Difficulty:** 3/5

### 21. ORTEX — Short Interest
- **URL:** https://docs.ortex.com / pip install `ortex`
- **Cost:** Paid (~$100+/mo), free trial
- **Data:** Short interest, cost to borrow, days to cover, utilisation
- **Integration:** Python SDK
- **Code:**
```python
import ortex
response = ortex.get_short_interest("NYSE", "AMC")
df = response.df
```
- **Difficulty:** 3/5

### 22. WhaleWisdom — 13F Holdings
- **URL:** https://whalewisdom.com/
- **Cost:** Standard $90/3mo, Pro $150/3mo
- **Data:** Institutional holdings changes (Buffett, Soros, etc.)
- **Integration:** REST API or scraping
- **Difficulty:** 3/5

### 23. SEC API (secapi.ai) — Insider Cluster Detection
- **URL:** https://docs.secapi.ai/use-cases/insider-trading-api
- **Cost:** Pay-as-you-go. Free tier available
- **Data:** Form 4 filings, cluster buying detection, webhook alerts
- **Integration:** REST API with Python/JS SDKs
- **Difficulty:** 2/5

### 24. Apify SEC Insider Trading Tracker
- **URL:** https://apify.com/ryanclinton/sec-insider-trading
- **Cost:** ~$0.002/transaction. Free tier: ~1,000 runs/month
- **Data:** AI-classified insider trades with cluster detection
- **Integration:** Apify actor API
- **Difficulty:** 2/5

---

## Category 4: Analyst Ratings & Recommendations

### 25. ⭐ FMP (Financial Modeling Prep) — Analyst Grades (FREE)
- **URL:** https://financialmodelingprep.com/stable/
- **Cost:** Free tier: 250 requests/day
- **Data:** Analyst upgrades/downgrades, grades, price targets
- **Integration:** REST API
- **Endpoints:**
```
GET /grades?symbol=AAPL → newGrade, previousGrade, action, gradingCompany
GET /api/v3/upgrades-downgrades?symbol=AAPL → Full history
```
- **Difficulty:** 1/5

### 26. Benzinga Calendar API — Analyst Ratings
- **URL:** https://api.benzinga.com/api/v2.1/calendar/ratings
- **Cost:** Free trial. Paid by volume
- **Data:** Detailed analyst actions with price target changes, analyst accuracy
- **Integration:** REST API
- **Difficulty:** 2/5

---

## Category 5: Pre/Post-Market Data

### 27. ⭐ Twelve Data — Extended Hours (FREE)
- **URL:** https://api.twelvedata.com/
- **Cost:** Free: 800 requests/day (delayed)
- **Data:** Pre/post-market OHLCV with `is_extended_hours` flag
- **Integration:** REST API
- **Code:**
```python
import requests
params = {"symbol": "AAPL", "prepost": "true", "apikey": "KEY"}
resp = requests.get("https://api.twelvedata.com/quote", params=params)
```
- **Difficulty:** 1/5

### 28. StockData.org — Extended Hours (FREE)
- **URL:** https://api.stockdata.org/v1/data/quote
- **Cost:** Free: 100 requests/day
- **Data:** Extended hours quotes + 7 years intraday history
- **Integration:** REST API
- **Difficulty:** 1/5

### 29. FMP — Aftermarket Quote & Trade
- **URL:** https://financialmodelingprep.com/stable/
- **Cost:** Free tier available
- **Data:** Dedicated aftermarket endpoints (bid/ask/volume outside hours)
- **Integration:** REST API
- **Difficulty:** 1/5

---

## Category 6: Macro & Alternative Data

### 30. ⭐ FRED API — Federal Reserve Economic Data (FREE)
- **URL:** https://fred.stlouisfed.org/docs/api/fred/
- **Cost:** COMPLETELY FREE
- **Auth:** Free API key (register at fred.stlouisfed.org)
- **Data:** 800,000+ time series: GDP, CPI, unemployment, Treasury yields, DXY
- **Integration:** `pip install fredapi` or REST API
- **Rate Limits:** 120 requests/minute
- **Code:**
```python
from fredapi import Fred
fred = Fred(api_key="YOUR_KEY")
# 10-year treasury yield
data = fred.get_series("DGS10")
# US Dollar Index
dxy = fred.get_series("DTWEXBGS")
```
- **Difficulty:** 1/5

### 31. FearGreedChart — Crypto + Stock Fear & Greed (FREE)
- **URL:** https://feargreedchart.com/
- **Cost:** COMPLETELY FREE. No auth
- **Data:** Stock market Fear & Greed (0-100), crypto F&G, BTC/ETH prices
- **Integration:** REST JSON
- **Code:**
```python
import requests
resp = requests.get("https://feargreedchart.com/?action=stock")
data = resp.json()
print(f"Stock F&G: {data['stock_fng']}/100")
```
- **Difficulty:** 1/5

### 32. CME Group — Futures Data
- **URL:** https://www.cmegroup.com/market-data.html
- **Cost:** Free delayed data
- **Data:** E-mini S&P futures, VIX futures, sector futures
- **Integration:** Direct CSV/API
- **Difficulty:** 2/5

---

## Category 7: Real-time & News

### 33. ⭐ Alpaca News API (FREE — Already Have Keys)
- **URL:** https://alpaca.markets/docs/api-references/market-data-api/news-data/
- **Cost:** FREE (already using Alpaca for trading)
- **Data:** News articles with sentiment, tickers mentioned
- **Integration:** Already have Alpaca client
- **Code:**
```python
from alpaca.data.requests import NewsRequest
request = NewsRequest(symbols=["AAPL"], limit=50)
news = client.get_news(request)
```
- **Difficulty:** 1/5
- **Why it's #1 priority:** Use existing Alpaca keys. Zero new setup

### 34. Benzinga API
- **URL:** https://www.benzinga.com/apis/cloud-product
- **Cost:** Free tier: 100 calls/day
- **Data:** News, earnings, analyst ratings, IPOs
- **Integration:** REST API
- **Difficulty:** 2/5

---

## Top 10 Recommendations (Ranked by Value/Ease)

### Tier 0: Implement Today (All Free, Zero Cost)

| Rank | Source | Why | Effort | Cost |
|------|--------|-----|--------|------|
| 1 | **Alpaca News API** | Already have Alpaca keys | 30 min | FREE |
| 2 | **yfinance Options Scanner** | Already installed | 1 hour | FREE |
| 3 | **FINRA Short Interest** | Regulatory data, no auth | 1 hour | FREE |
| 4 | **FRED Macro Data** | Treasury yields, DXY, GDP | 30 min | FREE |
| 5 | **FearGreedChart** | Market sentiment score | 15 min | FREE |
| 6 | **HackerNews Algolia** | Tech stock discussions | 30 min | FREE |

### Tier 1: Add This Week (Free Tiers)

| Rank | Source | Why | Effort | Cost |
|------|--------|-----|--------|------|
| 7 | **Telegram API** | High-signal stock channels | 1 hour | FREE |
| 8 | **Bluesky AT Protocol** | Growing finance community | 1 hour | FREE |
| 9 | **Adanos Sentiment** | One SDK = Reddit+X+News | 2 hours | Free 250 req/mo |
| 10 | **FMP Analyst Grades** | Upgrade/downgrade alerts | 1 hour | Free 250 req/day |
| 11 | **KeyVex** | Dark pool + Congress + 13F | 2 hours | Free 5K calls/mo |
| 12 | **Twelve Data** | Extended hours prices | 30 min | Free 800 req/day |
| 13 | **YouTube API** | Stock video comments | 1 hour | Free 10K quota/day |

### Tier 2: Worth Paying For

| Rank | Source | Cost | Why |
|------|--------|------|-----|
| 14 | **OptionWhales** | $19/mo | AI-scored unusual options flow |
| 15 | **QuiverQuant** | $30/mo | Congress + Insider + Dark Pool |
| 16 | **Unusual Whales API** | $150/mo | Real-time options + dark pool |
| 17 | **ORTEX** | ~$100/mo | Daily short interest (not twice-monthly) |

---

## Implementation Roadmap

### Phase 1: This Week (6 Free Sources)
- [ ] Alpaca News API
- [ ] yfinance Options scanner
- [ ] FINRA short interest
- [ ] FRED macro data
- [ ] FearGreedChart sentiment
- [ ] HackerNews Algolia

### Phase 2: Next Week (7 Free Sources)
- [ ] Telegram API
- [ ] Bluesky AT Protocol
- [ ] Adanos sentiment SDK
- [ ] FMP analyst grades
- [ ] KeyVex dark pool/congress
- [ ] Twelve Data extended hours
- [ ] YouTube comment sentiment

### Phase 3: Later (Paid Sources)
- [ ] OptionWhales ($19/mo)
- [ ] QuiverQuant ($30/mo)
- [ ] Unusual Whales API ($150/mo)

---

## The Reddit/Discord Problem & Replacement Strategy

**Current state:**
- Reddit: 403 blocked (needs real API credentials or VPN)
- Discord: Bot only in 1 guild, 22 channels inaccessible

**Free replacements:**
| Dead Source | Replacement | Why It's Better |
|-------------|-------------|-----------------|
| Reddit | **Telegram** | Active trading communities, no rate limits |
| Twitter/X | **Bluesky** | Free firehose, growing finance community |
| StockTwits | **Adanos SDK** | Aggregates Reddit+X+News in one call |
| Tech stocks | **HackerNews** | High-quality discussions, zero auth |

---

*Research completed by team of 3 specialist agents. 34 sources evaluated across 9 categories.*
