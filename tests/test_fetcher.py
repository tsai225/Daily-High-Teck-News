"""
tests/test_fetcher.py — Unit tests for src/fetcher.py
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.fetcher import _entry_id, _parse_date, _strip_html, fetch_feeds


class TestStripHtml:
    def test_removes_tags(self):
        assert _strip_html("<p>Hello <b>World</b></p>") == "Hello World"

    def test_collapses_whitespace(self):
        assert _strip_html("<p>  foo   bar  </p>") == "foo bar"

    def test_empty_string(self):
        assert _strip_html("") == ""

    def test_none_like_empty(self):
        # _strip_html is called with "" fallback; ensure no crash
        assert _strip_html("") == ""

    def test_preserves_text(self):
        assert _strip_html("no tags here") == "no tags here"


class TestParseDate:
    def _make_entry(self, parsed_tuple=None, published_str=None):
        entry = MagicMock()
        entry.published_parsed = parsed_tuple
        entry.updated_parsed = None
        entry.created_parsed = None
        entry.published = published_str
        entry.updated = None
        return entry

    def test_uses_parsed_tuple(self):
        t = (2024, 5, 1, 8, 0, 0, 2, 122, 0)
        entry = self._make_entry(parsed_tuple=t)
        result = _parse_date(entry)
        assert result is not None
        assert result.year == 2024
        assert result.month == 5
        assert result.tzinfo is not None

    def test_falls_back_to_string(self):
        entry = self._make_entry(published_str="2024-05-01T08:00:00+00:00")
        result = _parse_date(entry)
        assert result is not None
        assert result.year == 2024

    def test_returns_none_on_missing(self):
        entry = MagicMock()
        entry.published_parsed = None
        entry.updated_parsed = None
        entry.created_parsed = None
        entry.published = None
        entry.updated = None
        result = _parse_date(entry)
        assert result is None


class TestEntryId:
    def test_same_url_same_id(self):
        e1 = MagicMock()
        e1.link = "https://example.com/article"
        e1.title = "Hello World"
        e2 = MagicMock()
        e2.link = "https://example.com/article"
        e2.title = "Hello World"
        assert _entry_id(e1) == _entry_id(e2)

    def test_different_url_different_id(self):
        e1 = MagicMock()
        e1.link = "https://example.com/a"
        e1.title = "Title"
        e2 = MagicMock()
        e2.link = "https://example.com/b"
        e2.title = "Title"
        assert _entry_id(e1) != _entry_id(e2)


CONFIG_PATH = str(Path(__file__).parent.parent / "config" / "feeds.yml")


class TestFetchFeeds:
    def _make_fake_entry(self, title: str, link: str, pub: datetime):
        entry = MagicMock()
        entry.title = title
        entry.link = link
        entry.summary = "Test summary"
        entry.description = ""
        entry.published_parsed = pub.timetuple()[:6] + (0, 0, 0)
        entry.updated_parsed = None
        entry.created_parsed = None
        entry.published = pub.isoformat()
        entry.updated = None
        return entry

    @patch("src.fetcher.feedparser.parse")
    def test_filters_old_articles(self, mock_parse):
        now = datetime.now(tz=timezone.utc)
        old_pub = now - timedelta(hours=30)
        recent_pub = now - timedelta(hours=1)

        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.entries = [
            self._make_fake_entry("Old Article", "https://example.com/old", old_pub),
            self._make_fake_entry("Recent Article", "https://example.com/new", recent_pub),
        ]
        mock_parse.return_value = mock_feed

        articles = fetch_feeds(CONFIG_PATH, lookback_hours=24)
        titles = [a["title"] for a in articles]
        assert "Recent Article" in titles
        assert "Old Article" not in titles

    @patch("src.fetcher.feedparser.parse")
    def test_deduplicates_articles(self, mock_parse):
        now = datetime.now(tz=timezone.utc)
        pub = now - timedelta(hours=1)

        entry = self._make_fake_entry("Dup Article", "https://example.com/dup", pub)
        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.entries = [entry, entry]  # same entry twice
        mock_parse.return_value = mock_feed

        articles = fetch_feeds(CONFIG_PATH, lookback_hours=24)
        # Should only appear once per feed
        dup_count = sum(1 for a in articles if a["title"] == "Dup Article")
        assert dup_count == 1
