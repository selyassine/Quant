"""
M8 — News Intelligence
Collecte automatique d'actualités financières via RSS feeds.
Sources: Yahoo Finance, Reuters, Bloomberg RSS, Seeking Alpha, MarketWatch
"""
import httpx
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Dict, List, Optional
import logging
import re

logger = logging.getLogger(__name__)

# RSS feeds par ticker + feeds généraux
RSS_FEEDS = {
    "general": [
        "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^GSPC&region=US&lang=en-US",
        "https://feeds.reuters.com/reuters/businessNews",
        "https://www.marketwatch.com/rss/topstories",
    ],
    "AAPL":  ["https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL&region=US&lang=en-US"],
    "MSFT":  ["https://feeds.finance.yahoo.com/rss/2.0/headline?s=MSFT&region=US&lang=en-US"],
    "NVDA":  ["https://feeds.finance.yahoo.com/rss/2.0/headline?s=NVDA&region=US&lang=en-US"],
    "TSLA":  ["https://feeds.finance.yahoo.com/rss/2.0/headline?s=TSLA&region=US&lang=en-US"],
    "GOOGL": ["https://feeds.finance.yahoo.com/rss/2.0/headline?s=GOOGL&region=US&lang=en-US"],
    "SPY":   ["https://feeds.finance.yahoo.com/rss/2.0/headline?s=SPY&region=US&lang=en-US"],
    "BTC-USD": ["https://feeds.finance.yahoo.com/rss/2.0/headline?s=BTC-USD&region=US&lang=en-US"],
}

# Company keywords for matching news to tickers
TICKER_KEYWORDS = {
    "AAPL":    ["apple", "iphone", "ipad", "mac", "tim cook", "app store"],
    "MSFT":    ["microsoft", "azure", "windows", "copilot", "satya nadella", "xbox"],
    "NVDA":    ["nvidia", "gpu", "cuda", "jensen huang", "h100", "blackwell", "ai chip"],
    "TSLA":    ["tesla", "elon musk", "electric vehicle", "ev", "autopilot", "cybertruck"],
    "GOOGL":   ["google", "alphabet", "gemini", "youtube", "sundar pichai", "android"],
    "SPY":     ["s&p 500", "sp500", "stock market", "fed", "federal reserve", "inflation"],
    "QQQ":     ["nasdaq", "tech stocks", "technology sector"],
    "BTC-USD": ["bitcoin", "btc", "crypto", "cryptocurrency", "satoshi"],
    "ETH-USD": ["ethereum", "eth", "defi", "smart contract", "vitalik"],
}


class NewsCollector:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (compatible; QuantAI/1.0; +https://quantai.app)",
            "Accept": "application/rss+xml, application/xml, text/xml",
        }

    async def fetch_feed(self, url: str) -> List[Dict]:
        """Fetch and parse an RSS feed."""
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(url, headers=self.headers)
                if response.status_code != 200:
                    return []

                root = ET.fromstring(response.text)
                items = []

                # Handle both RSS 2.0 and Atom formats
                ns = {"atom": "http://www.w3.org/2005/Atom"}
                channel = root.find("channel")
                if channel is not None:
                    rss_items = channel.findall("item")
                else:
                    rss_items = root.findall(".//item")

                for item in rss_items[:10]:  # Max 10 per feed
                    title = item.findtext("title", "").strip()
                    link = item.findtext("link", "").strip()
                    pub_date = item.findtext("pubDate", "").strip()
                    description = item.findtext("description", "").strip()

                    # Clean HTML from description
                    description = re.sub(r"<[^>]+>", "", description)[:300]

                    if title:
                        items.append({
                            "title": title,
                            "url": link,
                            "published_at": pub_date,
                            "summary": description,
                            "source": url.split("/")[2],
                        })

                return items

        except Exception as e:
            logger.warning(f"Feed fetch failed {url}: {e}")
            return []

    async def collect_for_ticker(self, ticker: str, limit: int = 20) -> List[Dict]:
        """Collect news for a specific ticker."""
        all_articles = []

        # Ticker-specific feed
        feeds = RSS_FEEDS.get(ticker, []) + RSS_FEEDS["general"]

        for url in feeds[:3]:  # Max 3 feeds
            articles = await self.fetch_feed(url)
            all_articles.extend(articles)

        # Filter by relevance for general feeds
        keywords = TICKER_KEYWORDS.get(ticker, [ticker.lower()])
        relevant = []
        for article in all_articles:
            text = (article["title"] + " " + article["summary"]).lower()
            if any(kw in text for kw in keywords) or ticker.lower() in text:
                article["relevance"] = "high"
                relevant.append(article)
            elif ticker in RSS_FEEDS:  # ticker-specific feed = always relevant
                article["relevance"] = "medium"
                relevant.append(article)

        # Deduplicate by title
        seen = set()
        unique = []
        for a in relevant:
            if a["title"] not in seen:
                seen.add(a["title"])
                unique.append(a)

        return unique[:limit]

    async def collect_general(self, limit: int = 30) -> List[Dict]:
        """Collect general market news."""
        all_articles = []
        for url in RSS_FEEDS["general"]:
            articles = await self.fetch_feed(url)
            all_articles.extend(articles)

        seen = set()
        unique = []
        for a in all_articles:
            if a["title"] not in seen:
                seen.add(a["title"])
                unique.append(a)

        return unique[:limit]


news_collector = NewsCollector()
