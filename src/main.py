"""
src/main.py — Orchestration entry-point for the daily news pipeline.

Usage (GitHub Actions or local):
    python -m src.main

Environment variables (see sender.py and fetcher.py for full list):
    NEWS_LANGUAGE   — language hint stored in article metadata (default: en)
    TOP_N           — number of top articles to select (default: 10)
    LOOKBACK_HOURS  — how far back to look in RSS feeds (default: 24)
    CONFIG_PATH     — path to feeds.yml (default: config/feeds.yml)
    DAILY_DIR       — output directory for daily archives (default: daily)
    DRY_RUN         — if "true", skip actual email send and print instead
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytz

# Allow `python -m src.main` from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.fetcher import fetch_feeds
from src.ranker import rank_articles
from src.renderer import render_html, render_plaintext
from src.sender import send_email

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

TAIPEI_TZ = pytz.timezone("Asia/Taipei")


def _save_daily_archive(
    articles: list[dict],
    plain_body: str,
    daily_dir: str,
    report_date: datetime,
) -> None:
    """Persist daily markdown + JSON archives."""
    date_str = report_date.astimezone(TAIPEI_TZ).strftime("%Y-%m-%d")
    out_dir = Path(daily_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Markdown archive
    md_path = out_dir / f"{date_str}.md"
    md_path.write_text(plain_body, encoding="utf-8")
    logger.info("Saved markdown archive → %s", md_path)

    # JSON archive (serialisable subset)
    json_articles = []
    for art in articles:
        pub = art.get("published")
        json_articles.append(
            {
                "rank": art.get("rank"),
                "title": art.get("title"),
                "link": art.get("link"),
                "source": art.get("source"),
                "category": art.get("category"),
                "published": pub.isoformat() if pub else None,
                "score": art.get("score"),
                "summary": art.get("summary"),
            }
        )
    json_path = out_dir / f"{date_str}.json"
    json_path.write_text(json.dumps(json_articles, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Saved JSON archive → %s", json_path)


def main() -> None:
    config_path = os.environ.get("CONFIG_PATH", "config/feeds.yml")
    language = os.environ.get("NEWS_LANGUAGE", "en")
    top_n = int(os.environ.get("TOP_N", "10"))
    lookback_hours = int(os.environ.get("LOOKBACK_HOURS", "24"))
    daily_dir = os.environ.get("DAILY_DIR", "daily")
    dry_run = os.environ.get("DRY_RUN", "false").lower() == "true"

    now_utc = datetime.now(tz=timezone.utc)
    report_date = now_utc.astimezone(TAIPEI_TZ)
    date_str = report_date.strftime("%Y-%m-%d")

    logger.info("=== Daily Tech News Pipeline ===")
    logger.info("Report date (Taipei): %s | TOP_N=%d | LOOKBACK_HOURS=%d", date_str, top_n, lookback_hours)

    # 1. Fetch
    logger.info("Step 1/4 — Fetching feeds …")
    articles = fetch_feeds(config_path, lookback_hours=lookback_hours, language=language)

    if not articles:
        logger.warning("No articles fetched. Sending empty report.")

    # 2. Rank
    logger.info("Step 2/4 — Ranking articles …")
    top_articles = rank_articles(articles, config_path, top_n=top_n, now=now_utc)

    # 3. Render
    logger.info("Step 3/4 — Rendering email …")
    subject = f"🌐 每日全球前沿科技新聞 Top {top_n} — {date_str}"
    html_body = render_html(top_articles, report_date=report_date)
    plain_body = render_plaintext(top_articles, report_date=report_date)

    # Save daily archive
    _save_daily_archive(top_articles, plain_body, daily_dir, report_date)

    # 4. Send
    logger.info("Step 4/4 — Sending email …")
    if dry_run:
        logger.info("[DRY RUN] Skipping actual email send. Plain text preview:\n%s", plain_body)
    else:
        send_email(subject, html_body, plain_body)

    logger.info("=== Pipeline complete ===")


if __name__ == "__main__":
    main()
