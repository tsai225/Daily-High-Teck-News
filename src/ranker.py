"""
src/ranker.py — Score and select Top-N articles.

Scoring formula (all components normalised 0-1 before weighting):
  score = (recency * 0.35) + (keyword * 0.30) + (source_weight * 0.20) + (category_novelty * 0.15)
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Category novelty bonus: we reward diversity by bumping the first article
# from each category by a small fixed amount.
_CATEGORY_NOVELTY_BONUS = 0.15


def _load_keyword_config(config_path: str) -> dict[str, Any]:
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _keyword_score(text: str, keyword_boosts: dict[str, list[str]]) -> float:
    """
    Return a normalised keyword score in [0, 1].
    tier1 words score +0.4, tier2 +0.2, tier3 +0.1, capped at 1.0.
    """
    lower = text.lower()
    raw = 0.0
    for word in keyword_boosts.get("tier1", []):
        if word.lower() in lower:
            raw += 0.4
    for word in keyword_boosts.get("tier2", []):
        if word.lower() in lower:
            raw += 0.2
    for word in keyword_boosts.get("tier3", []):
        if word.lower() in lower:
            raw += 0.1
    return min(raw, 1.0)


def _recency_score(published: datetime | None, now: datetime, max_hours: float = 24.0) -> float:
    """
    Linear decay: 1.0 for just-published, 0.0 for articles at the cutoff.
    Articles with no publish date get 0.5.
    """
    if published is None:
        return 0.5
    age_hours = (now - published).total_seconds() / 3600.0
    age_hours = max(0.0, min(age_hours, max_hours))
    return 1.0 - (age_hours / max_hours)


def _source_score(weight: float, max_weight: float = 2.0) -> float:
    """Normalise source weight to [0, 1]."""
    return min(weight, max_weight) / max_weight


def rank_articles(
    articles: list[dict[str, Any]],
    config_path: str,
    top_n: int = 10,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """
    Score every article, sort descending, add diversity boost, return top_n.
    Mutates each dict in *articles* by adding a 'score' key.
    """
    if not articles:
        return []

    cfg = _load_keyword_config(config_path)
    keyword_boosts = cfg.get("keyword_boosts", {})

    if now is None:
        now = datetime.now(tz=timezone.utc)

    for art in articles:
        combined_text = f"{art.get('title', '')} {art.get('summary', '')}"
        r = _recency_score(art.get("published"), now)
        k = _keyword_score(combined_text, keyword_boosts)
        s = _source_score(art.get("weight", 1.0))

        art["score"] = round(r * 0.35 + k * 0.30 + s * 0.20, 4)

    # Sort by score desc; then by published desc as tiebreaker
    articles.sort(
        key=lambda a: (a["score"], a.get("published") or datetime.min.replace(tzinfo=timezone.utc)),
        reverse=True,
    )

    # Diversity pass: ensure at least one article per category in top_n
    seen_categories: set[str] = set()
    top: list[dict[str, Any]] = []
    remainder: list[dict[str, Any]] = []

    for art in articles:
        cat = art.get("category", "general")
        if cat not in seen_categories:
            art["score"] = round(art["score"] + _CATEGORY_NOVELTY_BONUS, 4)
            seen_categories.add(cat)
            top.append(art)
        else:
            remainder.append(art)

    # Fill up to top_n
    combined = top + remainder
    combined.sort(
        key=lambda a: (a["score"], a.get("published") or datetime.min.replace(tzinfo=timezone.utc)),
        reverse=True,
    )

    selected = combined[:top_n]
    for i, art in enumerate(selected, start=1):
        art["rank"] = i

    logger.info("Top %d articles selected (from %d total)", len(selected), len(articles))
    return selected
