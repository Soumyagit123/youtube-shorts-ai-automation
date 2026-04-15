"""
modules/researcher.py — Trending Topic Finder
=============================================
Priority order:
  1. Google Trends via pytrends (real-time top queries)
  2. RSS feeds fallback (TechCrunch, The Verge, Ars Technica)

Returns a single string — the best trending AI/Tech topic to create a Short about.
"""

import random
import time
import feedparser
import requests
import asyncio
from pytrends.request import TrendReq

from config import get_logger, DEFAULT_TOPICS
from core.utils import get_user_conf

log = get_logger("researcher")

# ── RSS Feed URLs (AI/Tech) ────────────────────────────────────────────────────
RSS_FEEDS = [
    "https://techcrunch.com/feed/",
    "https://www.theverge.com/rss/index.xml",
    "https://feeds.arstechnica.com/arstechnica/technology-lab",
    "https://venturebeat.com/feed/",
    "https://www.wired.com/feed/rss",
]

# Keywords used to filter for AI/Tech relevance
AI_KEYWORDS = [
    "ai", "artificial intelligence", "machine learning", "deep learning",
    "gpt", "llm", "robot", "automation", "neural", "tech", "openai",
    "google", "microsoft", "nvidia", "chip", "quantum", "model", "agent",
]


def _is_ai_tech(text: str) -> bool:
    """Return True if text contains at least one AI/tech keyword."""
    lower = text.lower()
    return any(kw in lower for kw in AI_KEYWORDS)


async def _fetch_from_pytrends() -> str | None:
    """Fetch the top trending AI/Tech search query from Google Trends."""
    try:
        def _query():
            log.debug("Querying Google Trends …")
            pytrends = TrendReq(hl="en-US", tz=330)

            # Get real-time trending searches (US)
            trending_df = pytrends.trending_searches(pn="united_states")
            candidates = trending_df[0].tolist()

            # Filter for AI/tech topics
            ai_topics = [t for t in candidates if _is_ai_tech(t)]
            if ai_topics:
                return ai_topics[0]

            # If nothing matched, try a keyword-based related query
            pytrends.build_payload(["artificial intelligence"], cat=0, timeframe="now 1-d")
            related = pytrends.related_queries()
            top_queries = related.get("artificial intelligence", {}).get("top")
            if top_queries is not None and not top_queries.empty:
                return top_queries.iloc[0]["query"]
            return None

        chosen = await asyncio.to_thread(_query)
        if chosen:
            log.info(f"pytrends → chosen topic: {chosen!r}")
            return chosen

    except Exception as exc:
        log.debug(f"pytrends unavailable ({exc}) — falling back to RSS silently")
    return None


async def _fetch_from_rss() -> str | None:
    """Scrape RSS feeds and return the most relevant AI/Tech headline."""
    log.debug("Fetching from RSS feeds …")
    
    def _parse_all():
        headlines: list[str] = []
        for url in RSS_FEEDS:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:10]:
                    title = entry.get("title", "")
                    if _is_ai_tech(title):
                        headlines.append(title)
            except Exception as exc:
                log.warning(f" RSS parse error ({url}): {exc}")
        return headlines

    headlines = await asyncio.to_thread(_parse_all)

    if headlines:
        chosen = random.choice(headlines)
        log.info(f"RSS → chosen topic: {chosen!r}")
        return chosen

    return None


async def find_trending_topic(user_config: dict | None = None) -> str:
    """
    Public entry point — returns a trending AI/Tech topic string.
    Tries pytrends first, falls back to RSS, then uses a safe default.
    """
    topic = await _fetch_from_pytrends()
    if not topic:
        topic = await _fetch_from_rss()
    if not topic:
        topic = random.choice(DEFAULT_TOPICS)
        log.warning(f"All sources failed — using random default topic: {topic!r}")

    return topic


if __name__ == "__main__":
    # Quick smoke-test
    print(f"\n🔥 Trending topic: {find_trending_topic()}")
