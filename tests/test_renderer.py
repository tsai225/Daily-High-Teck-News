"""
tests/test_renderer.py — Unit tests for src/renderer.py
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
import pytz

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.renderer import _excerpt, _format_pub_time, render_html, render_plaintext

TAIPEI_TZ = pytz.timezone("Asia/Taipei")


def _make_article(rank=1, title="Test Article", link="https://example.com/1",
                  source="Test Source", category="ai", published=None, summary="Test summary"):
    if published is None:
        published = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
    return {
        "rank": rank,
        "title": title,
        "link": link,
        "source": source,
        "category": category,
        "published": published,
        "summary": summary,
        "score": 0.75,
    }


class TestExcerpt:
    def test_short_text_unchanged(self):
        assert _excerpt("hello", 200) == "hello"

    def test_long_text_truncated(self):
        long = "word " * 100
        result = _excerpt(long, 50)
        assert len(result) <= 55  # some slack for placeholder

    def test_adds_ellipsis(self):
        long = "a" * 300
        result = _excerpt(long, 200)
        assert result.endswith("…")


class TestFormatPubTime:
    def test_none_returns_unknown(self):
        assert _format_pub_time(None) == "未知時間"

    def test_returns_taipei_time(self):
        # 2024-05-01 00:00 UTC = 2024-05-01 08:00 Taipei
        dt = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        result = _format_pub_time(dt)
        assert "2024-05-01" in result
        assert "08:00" in result


class TestRenderHtml:
    def test_returns_html_string(self):
        arts = [_make_article(i) for i in range(1, 4)]
        html = render_html(arts)
        assert "<!DOCTYPE html>" in html
        assert "<html" in html

    def test_contains_article_title(self):
        arts = [_make_article(title="My Unique Article Title")]
        html = render_html(arts)
        assert "My Unique Article Title" in html

    def test_contains_link(self):
        arts = [_make_article(link="https://unique-link.example.com/abc")]
        html = render_html(arts)
        assert "https://unique-link.example.com/abc" in html

    def test_contains_rank(self):
        arts = [_make_article(rank=7)]
        html = render_html(arts)
        assert "#7" in html

    def test_empty_articles(self):
        html = render_html([])
        assert "<!DOCTYPE html>" in html

    def test_html_escapes_special_chars(self):
        arts = [_make_article(title="<script>alert('xss')</script>")]
        html = render_html(arts)
        assert "<script>" not in html


class TestRenderPlaintext:
    def test_returns_string(self):
        arts = [_make_article()]
        result = render_plaintext(arts)
        assert isinstance(result, str)

    def test_contains_rank_prefix(self):
        arts = [_make_article(rank=3)]
        result = render_plaintext(arts)
        assert "#3" in result

    def test_contains_title(self):
        arts = [_make_article(title="Unique Plaintext Title")]
        result = render_plaintext(arts)
        assert "Unique Plaintext Title" in result

    def test_contains_link(self):
        arts = [_make_article(link="https://plaintext-link.example.com")]
        result = render_plaintext(arts)
        assert "https://plaintext-link.example.com" in result

    def test_contains_date_header(self):
        report_date = datetime(2024, 5, 1, 8, 0, 0, tzinfo=TAIPEI_TZ)
        arts = [_make_article()]
        result = render_plaintext(arts, report_date=report_date)
        assert "2024-05-01" in result
