"""
tests/test_ranker.py — Unit tests for src/ranker.py
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ranker import _keyword_score, _recency_score, _source_score, rank_articles

CONFIG_PATH = str(Path(__file__).parent.parent / "config" / "feeds.yml")


class TestRecencyScore:
    def test_just_published_is_one(self):
        now = datetime.now(tz=timezone.utc)
        assert _recency_score(now, now) == pytest.approx(1.0)

    def test_at_cutoff_is_zero(self):
        now = datetime.now(tz=timezone.utc)
        pub = now - timedelta(hours=24)
        assert _recency_score(pub, now) == pytest.approx(0.0)

    def test_midpoint_is_half(self):
        now = datetime.now(tz=timezone.utc)
        pub = now - timedelta(hours=12)
        assert _recency_score(pub, now) == pytest.approx(0.5)

    def test_none_returns_half(self):
        now = datetime.now(tz=timezone.utc)
        assert _recency_score(None, now) == pytest.approx(0.5)


class TestSourceScore:
    def test_weight_1_is_half(self):
        assert _source_score(1.0) == pytest.approx(0.5)

    def test_weight_2_is_one(self):
        assert _source_score(2.0) == pytest.approx(1.0)

    def test_weight_above_max_capped(self):
        assert _source_score(5.0) == pytest.approx(1.0)


class TestKeywordScore:
    BOOSTS = {
        "tier1": ["breakthrough"],
        "tier2": ["AI", "chip"],
        "tier3": ["cloud"],
    }

    def test_tier1_match(self):
        score = _keyword_score("Major breakthrough in computing", self.BOOSTS)
        assert score >= 0.4

    def test_tier2_match(self):
        score = _keyword_score("New AI chip announced", self.BOOSTS)
        assert score >= 0.4  # two tier2 matches

    def test_no_match(self):
        assert _keyword_score("Sports news today", self.BOOSTS) == 0.0

    def test_capped_at_one(self):
        # Use extra keywords so raw score exceeds 1.0, capped at exactly 1.0
        boosts_high = {
            "tier1": ["breakthrough"],           # +0.4
            "tier2": ["AI", "chip", "quantum", "space"],  # 4 × +0.2 = +0.8  → raw 1.2
            "tier3": [],
        }
        score = _keyword_score("AI chip breakthrough quantum space", boosts_high)
        assert score == pytest.approx(1.0)

    def test_case_insensitive(self):
        score_lower = _keyword_score("artificial intelligence ai", self.BOOSTS)
        score_upper = _keyword_score("Artificial Intelligence AI", self.BOOSTS)
        assert score_lower == score_upper


def _make_articles(n: int, now: datetime | None = None) -> list[dict]:
    if now is None:
        now = datetime.now(tz=timezone.utc)
    articles = []
    categories = ["ai", "chips", "security", "cloud", "research", "general", "robotics", "space", "biotech", "quantum"]
    for i in range(n):
        articles.append(
            {
                "id": f"id-{i}",
                "title": f"Tech Article {i}",
                "link": f"https://example.com/{i}",
                "source": f"Source {i}",
                "category": categories[i % len(categories)],
                "weight": 1.0 + (i % 3) * 0.25,
                "published": now - timedelta(hours=i),
                "summary": "AI chip quantum breakthrough cloud robotics",
            }
        )
    return articles


class TestRankArticles:
    def test_returns_top_n(self):
        arts = _make_articles(30)
        top = rank_articles(arts, CONFIG_PATH, top_n=10)
        assert len(top) == 10

    def test_rank_field_assigned(self):
        arts = _make_articles(15)
        top = rank_articles(arts, CONFIG_PATH, top_n=10)
        ranks = [a["rank"] for a in top]
        assert ranks == list(range(1, 11))

    def test_score_field_exists(self):
        arts = _make_articles(5)
        top = rank_articles(arts, CONFIG_PATH, top_n=5)
        for a in top:
            assert "score" in a
            assert 0.0 <= a["score"] <= 1.5  # diversity bonus can push above 1.0

    def test_empty_input_returns_empty(self):
        assert rank_articles([], CONFIG_PATH) == []

    def test_fewer_than_top_n_returns_all(self):
        arts = _make_articles(3)
        top = rank_articles(arts, CONFIG_PATH, top_n=10)
        assert len(top) == 3

    def test_scores_are_deterministic(self):
        now = datetime(2024, 5, 1, 8, 0, 0, tzinfo=timezone.utc)
        arts1 = _make_articles(20, now=now)
        arts2 = _make_articles(20, now=now)
        top1 = rank_articles(arts1, CONFIG_PATH, top_n=10, now=now)
        top2 = rank_articles(arts2, CONFIG_PATH, top_n=10, now=now)
        assert [a["id"] for a in top1] == [a["id"] for a in top2]
