# Daily High-Tech News 🌐

每天早上 8:50（台北時間）自動抓取全球最新前沿科技新聞，選出 **Top 10**，寄送到您的信箱。

Automated daily pipeline that searches global cutting-edge technology news, selects the top 10 most important items, and emails them before **09:00 Asia/Taipei**.

---

## 功能特色 Features

| 項目 | 說明 |
|------|------|
| 📡 **新聞來源** | 30+ RSS 來源：AI、晶片、資安、雲端、研究、太空、生技、量子等 |
| 🏆 **智慧排名** | 時效性 × 關鍵字加權 × 來源品質 × 類別多元性 |
| 📧 **HTML 郵件** | 美觀 HTML + 純文字雙格式，繁體中文界面 |
| 🗄️ **每日存檔** | 自動 commit `daily/YYYY-MM-DD.md` + `.json` 到 repo |
| 🔒 **無硬編碼密鑰** | 所有密碼通過 GitHub Secrets 注入 |

---

## 快速設定 Quick Setup

### 1. 建立 Gmail App Password

1. 至 [Google 帳戶安全性](https://myaccount.google.com/security) 確認已啟用兩步驟驗證
2. 前往 [App Passwords](https://myaccount.google.com/apppasswords)
3. 新增一組密碼（應用程式：Mail；裝置：GitHub Actions）
4. 複製產生的 16 碼密碼

### 2. 設定 GitHub Secrets

至 **Settings → Secrets and variables → Actions → New repository secret** 新增：

| Secret 名稱 | 說明 | 必填 |
|-------------|------|------|
| `SMTP_USERNAME` | Gmail 寄件地址，例如 `you@gmail.com` | ✅ |
| `SMTP_PASSWORD` | Gmail App Password（步驟 1 取得） | ✅ |
| `MAIL_TO` | 收件地址（可多個，用逗號分隔） | ✅ |
| `MAIL_FROM` | 寄件顯示地址（預設同 `SMTP_USERNAME`） | ☑️ |
| `MAIL_CC` | 副本收件者（逗號分隔） | ☑️ |
| `NEWS_LANGUAGE` | 語言提示，預設 `en` | ☑️ |
| `TOP_N` | 顯示前幾則，預設 `10` | ☑️ |

### 3. 啟用 Workflow

Workflow 已設定為每天 **00:50 UTC（08:50 台北時間）** 自動執行。
確認 repo 的 Actions 功能已啟用即可。

---

## 手動觸發 Manual Trigger

1. 前往 **Actions → Daily Tech News → Run workflow**
2. 可選填 `top_n`（篇數）與 `dry_run`（不實際寄信，用於測試）

---

## 本地測試 Local Testing

```bash
# 安裝相依套件
pip install -r requirements.txt

# 設定環境變數（替換成真實值）
export SMTP_USERNAME="you@gmail.com"
export SMTP_PASSWORD="your-app-password"
export MAIL_TO="you@gmail.com"

# 試跑（dry_run=true 不寄信）
DRY_RUN=true python -m src.main

# 執行單元測試
pytest tests/ -v
```

---

## 專案結構 Project Structure

```
.
├── .github/
│   └── workflows/
│       └── daily-news.yml     # GitHub Actions 排程
├── config/
│   └── feeds.yml              # RSS 來源清單 + 關鍵字設定
├── src/
│   ├── fetcher.py             # 抓取 RSS，過濾 24h 內，去重
│   ├── ranker.py              # 評分排名，選出 Top N
│   ├── renderer.py            # 產生 HTML + 純文字郵件
│   ├── sender.py              # Gmail SMTP 寄信
│   └── main.py                # 主流程進入點
├── tests/
│   ├── test_fetcher.py
│   ├── test_ranker.py
│   └── test_renderer.py
├── daily/                     # 每日存檔（自動 commit）
├── requirements.txt
└── README.md
```

---

## 評分邏輯 Scoring Logic

```
score = recency(0.35) + keyword_boost(0.30) + source_quality(0.20) + diversity_bonus(0.15)
```

- **recency**: 剛發布 = 1.0，24 小時前 = 0.0，線性衰減
- **keyword_boost**: AI/量子/晶片/資安/突破等關鍵詞加權
- **source_quality**: 不同來源預設權重（arXiv/MIT TR/Ars Technica 等較高）
- **diversity_bonus**: 每個類別的第一篇文章額外加分，確保類別多元

---

## 新聞來源 News Sources

| 類別 | 來源 |
|------|------|
| 🤖 AI | OpenAI Blog, Google AI, DeepMind, Hugging Face, The Batch |
| 🔬 研究 | arXiv (cs.AI/LG), MIT Technology Review, Nature, IEEE Spectrum |
| 💻 晶片 | AnandTech, Tom's Hardware, SemiAnalysis |
| 🔐 資安 | Krebs on Security, Schneier, The Hacker News, Dark Reading |
| ☁️ 雲端 | AWS Blog, Google Cloud Blog, Azure Blog |
| 🚀 太空 | SpaceNews, NASA News |
| 🧬 生技 | STAT News, BioPharma Dive |
| ⚛️ 量子 | Quantum Computing Report |
| 📰 綜合 | Ars Technica, The Verge, Wired, TechCrunch, Hacker News |

> 可於 `config/feeds.yml` 自訂來源清單與關鍵字權重。

---

## 授權 License

MIT
