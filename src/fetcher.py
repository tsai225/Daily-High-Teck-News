"""
src/fetcher.py — Fetch RSS feeds, filter to last 24 h, deduplicate.
"""
from __future__ import annotations

import hashlib
import logging
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

import feedparser
import yaml
from bs4 import BeautifulSoup
from dateutil import parser as dateutil_parser

logger = logging.getLogger(__name__)

# Maximum seconds to wait for a single feed
FEED_TIMEOUT = 15
# Maximum entries kept per feed before scoring
MAX_ENTRIES_PER_FEED = 30


def _load_config(config_path: str) -> dict[str, Any]:
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _strip_html(raw: str) -> str:
    """Remove HTML tags and collapse whitespace."""
    text = BeautifulSoup(raw or "", "html.parser").get_text(separator=" ")
    return re.sub(r"\s+", " ", text).strip()


def _parse_date(entry: feedparser.FeedParserDict) -> datetime | None:
    """Return a timezone-aware UTC datetime from an RSS entry, or None."""
    for attr in ("published_parsed", "updated_parsed", "created_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except (ValueError, TypeError):
                pass
    # Fall back to string fields
    for attr in ("published", "updated"):
        raw = getattr(entry, attr, None)
        if raw:
            try:
                dt = dateutil_parser.parse(raw)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except (ValueError, TypeError):
                pass
    return None


def _entry_id(entry: feedparser.FeedParserDict) -> str:
    """Deterministic content-based ID for deduplication."""
    url = getattr(entry, "link", "") or ""
    title = getattr(entry, "title", "") or ""
    raw = f"{url}|{title.lower().strip()}"
    return hashlib.md5(raw.encode()).hexdigest()


def fetch_feeds(
    config_path: str,
    lookback_hours: int = 24,
    language: str = "en",
) -> list[dict[str, Any]]:
    """
    Fetch all configured RSS feeds and return a deduplicated list of articles
    published within the last *lookback_hours* hours.

    Each article dict contains:
        id, title, link, source, category, weight,
        published (datetime UTC), summary, language
    """
    config = _load_config(config_path)
    feeds_cfg: list[dict] = config.get("feeds", [])

    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=lookback_hours)
    seen_ids: set[str] = set()
    articles: list[dict[str, Any]] = []

    for feed_def in feeds_cfg:
        url = feed_def.get("url", "")
        name = feed_def.get("name", urlparse(url).netloc)
        category = feed_def.get("category", "general")
        weight = float(feed_def.get("weight", 1.0))

        try:
            parsed = feedparser.parse(url, request_headers={"User-Agent": "DailyTechNewsBot/1.0"})
        except Exception as exc:
            logger.warning("Failed to fetch %s: %s", name, exc)
            continue

        if parsed.bozo and not parsed.entries:
            logger.warning("Bozo feed (no entries) for %s", name)
            continue

        count = 0
        for entry in parsed.entries[:MAX_ENTRIES_PER_FEED]:
            pub_dt = _parse_date(entry)
            if pub_dt and pub_dt < cutoff:
                continue  # too old

            aid = _entry_id(entry)
            if aid in seen_ids:
                continue
            seen_ids.add(aid)

            raw_summary = (
                getattr(entry, "summary", "")
                or getattr(entry, "description", "")
                or ""
            )
            summary = _strip_html(raw_summary)[:500]
            title = _strip_html(getattr(entry, "title", "") or "")
            link = getattr(entry, "link", "") or ""

            if not title or not link:
                continue

            articles.append(
                {
                    "id": aid,
                    "title": title,
                    "link": link,
                    "source": name,
                    "category": category,
                    "weight": weight,
                    "published": pub_dt,
                    "summary": summary,
                    "language": language,
                }
            )
            count += 1

        logger.info("Fetched %d articles from %s", count, name)

    logger.info("Total articles fetched (deduped): %d", len(articles))
    return articles
