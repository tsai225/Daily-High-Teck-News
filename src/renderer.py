"""
src/renderer.py — Build HTML + plain-text email bodies from ranked articles.

Output language: Traditional Chinese (zh-TW) with English titles preserved.
No external translation API required — we use bilingual layout.
"""
from __future__ import annotations

import html
import textwrap
from datetime import datetime, timezone
from typing import Any

import pytz

TAIPEI_TZ = pytz.timezone("Asia/Taipei")

# Category display names in zh-TW
CATEGORY_ZH: dict[str, str] = {
    "ai": "人工智慧",
    "research": "研究前沿",
    "chips": "晶片半導體",
    "security": "資訊安全",
    "cloud": "雲端運算",
    "robotics": "機器人",
    "space": "太空科技",
    "biotech": "生物科技",
    "quantum": "量子運算",
    "general": "科技新聞",
}


def _format_pub_time(pub: datetime | None) -> str:
    if pub is None:
        return "未知時間"
    local = pub.astimezone(TAIPEI_TZ)
    return local.strftime("%Y-%m-%d %H:%M (台北時間)")


def _excerpt(text: str, max_chars: int = 200) -> str:
    """Return a clean excerpt, word-wrapped at max_chars."""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return textwrap.shorten(text, width=max_chars, placeholder="…")


def render_html(articles: list[dict[str, Any]], report_date: datetime | None = None) -> str:
    """Return a complete HTML email body."""
    if report_date is None:
        report_date = datetime.now(tz=TAIPEI_TZ)
    date_str = report_date.astimezone(TAIPEI_TZ).strftime("%Y 年 %m 月 %d 日")

    items_html = ""
    for art in articles:
        rank = art.get("rank", "?")
        title = html.escape(art.get("title", "（無標題）"))
        link = html.escape(art.get("link", "#"))
        source = html.escape(art.get("source", ""))
        category_key = art.get("category", "general")
        category_zh = CATEGORY_ZH.get(category_key, category_key)
        pub_str = _format_pub_time(art.get("published"))
        summary = html.escape(_excerpt(art.get("summary", ""), 300))

        items_html += f"""
        <tr>
          <td style="padding:12px 8px;vertical-align:top;font-size:22px;font-weight:bold;
                     color:#1a73e8;width:36px;">#{rank}</td>
          <td style="padding:12px 8px;vertical-align:top;">
            <p style="margin:0 0 4px 0;">
              <a href="{link}" style="font-size:16px;font-weight:bold;color:#1a1a1a;
                 text-decoration:none;">{title}</a>
            </p>
            <p style="margin:0 0 6px 0;font-size:12px;color:#888888;">
              📰 {source} &nbsp;|&nbsp; 🏷️ {category_zh} &nbsp;|&nbsp; 🕐 {pub_str}
            </p>
            <p style="margin:0;font-size:14px;color:#444444;line-height:1.6;">{summary}</p>
            <p style="margin:6px 0 0 0;">
              <a href="{link}" style="font-size:12px;color:#1a73e8;">閱讀全文 →</a>
            </p>
          </td>
        </tr>
        <tr><td colspan="2" style="padding:0 8px;">
          <hr style="border:none;border-top:1px solid #eeeeee;margin:0;">
        </td></tr>
"""

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>每日全球前沿科技新聞 Top 10 — {date_str}</title>
</head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:'Helvetica Neue',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;padding:24px 0;">
    <tr>
      <td align="center">
        <table width="680" cellpadding="0" cellspacing="0"
               style="background:#ffffff;border-radius:8px;overflow:hidden;
                      box-shadow:0 2px 8px rgba(0,0,0,0.08);">
          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#1a73e8,#0d47a1);
                       padding:28px 32px;text-align:center;">
              <h1 style="margin:0;color:#ffffff;font-size:22px;font-weight:700;letter-spacing:1px;">
                🌐 每日全球前沿科技新聞 Top 10
              </h1>
              <p style="margin:8px 0 0 0;color:#c5e3ff;font-size:14px;">{date_str}</p>
            </td>
          </tr>
          <!-- Body -->
          <tr>
            <td style="padding:16px 24px;">
              <table width="100%" cellpadding="0" cellspacing="0">
{items_html}
              </table>
            </td>
          </tr>
          <!-- Footer -->
          <tr>
            <td style="background:#f8f9fa;padding:16px 24px;text-align:center;
                       font-size:11px;color:#aaaaaa;border-top:1px solid #eeeeee;">
              此郵件由 Daily-High-Tech-News GitHub Actions 自動產生 ·
              <a href="https://github.com/tsai225/Daily-High-Teck-News"
                 style="color:#1a73e8;text-decoration:none;">查看原始碼</a>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def render_plaintext(articles: list[dict[str, Any]], report_date: datetime | None = None) -> str:
    """Return a plain-text email body (fallback for non-HTML clients)."""
    if report_date is None:
        report_date = datetime.now(tz=TAIPEI_TZ)
    date_str = report_date.astimezone(TAIPEI_TZ).strftime("%Y-%m-%d")

    lines = [
        f"每日全球前沿科技新聞 Top 10 — {date_str}",
        "=" * 60,
        "",
    ]
    for art in articles:
        rank = art.get("rank", "?")
        title = art.get("title", "（無標題）")
        link = art.get("link", "")
        source = art.get("source", "")
        category_key = art.get("category", "general")
        category_zh = CATEGORY_ZH.get(category_key, category_key)
        pub_str = _format_pub_time(art.get("published"))
        excerpt = _excerpt(art.get("summary", ""), 250)

        lines += [
            f"#{rank}  {title}",
            f"    來源: {source}  |  類別: {category_zh}  |  {pub_str}",
            f"    {excerpt}",
            f"    🔗 {link}",
            "",
            "-" * 60,
            "",
        ]

    lines.append("此郵件由 Daily-High-Tech-News GitHub Actions 自動產生")
    lines.append("https://github.com/tsai225/Daily-High-Teck-News")
    return "\n".join(lines)
