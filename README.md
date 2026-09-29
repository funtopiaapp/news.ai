# news.ai

A personal hourly news briefing site. Static HTML, rebuilt and published
every hour by GitHub Actions - no server, no database, no running costs.

## How it works

1. `.github/workflows/update.yml` runs every hour (cron `11 * * * *`).
2. `fetch.py` pulls Google News RSS feeds for each section into `data/raw.json`.
3. `build.py` renders `site/` (index + one page per section).
4. The fresh `data/raw.json` is committed back; the site is deployed to
   GitHub Pages via `upload-pages-artifact` / `deploy-pages`.

## Sections

immigration (EB-1 & L-1A) · ai-tech · us-markets · india-markets ·
us-news · india-news · kerala (Kerala/Kochi/Haripad/Kollam/Alappuzha) ·
bangalore · airlines · nc-colleges (evergreen NC college guide + news)

## Setup

1. Create a public repo named `news-ai`, push this directory to `main`.
2. Repo Settings -> Pages -> Source: **GitHub Actions**.
3. Done. The workflow publishes to `https://<user>.github.io/news-ai/`.

## Local test

    python3 fetch.py && python3 build.py
    # open site/index.html
