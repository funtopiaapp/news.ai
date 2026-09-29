#!/usr/bin/env python3
"""news.ai fetcher - pull Google News RSS per section, save data/raw.json.

Run: python3 fetch.py
Writes: data/raw.json (replaced each run).
Failures are per-feed; a dead feed doesn't kill the run.
"""
import html as htmlmod
import json
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")
os.makedirs(DATA_DIR, exist_ok=True)

UA = {"User-Agent": "news-ai/1.0 (personal news aggregator)"}
PER_SECTION_CAP = 25


def search_url(query, country="US"):
    q = urllib.parse.quote(query)
    if country == "IN":
        return f"https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
    return f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


def topic_url(topic, country="US"):
    if country == "IN":
        return (f"https://news.google.com/rss/headlines/section/topic/{topic}"
                "?hl=en-IN&gl=IN&ceid=IN:en")
    return (f"https://news.google.com/rss/headlines/section/topic/{topic}"
            "?hl=en-US&gl=US&ceid=US:en")


SECTIONS = {
    "immigration": {
        "title": "Immigration: EB-1 & L-1A",
        "blurb": "Green-card and work-visa news that matters for EB-1 and L-1A holders.",
        "feeds": [
            ("EB-1 updates", search_url("(EB-1 OR EB1) green card visa bulletin")),
            ("L-1A news", search_url("L-1A visa")),
        ],
    },
    "ai-tech": {
        "title": "AI & Technology",
        "blurb": "AI breakthroughs, model releases, and big tech moves.",
        "feeds": [
            ("AI news", search_url("artificial intelligence")),
            ("Tech headlines", topic_url("TECHNOLOGY")),
        ],
    },
    "us-markets": {
        "title": "US Markets",
        "blurb": "US stocks, trending tickers, ETFs, mutual funds, and what big funds are buying.",
        "feeds": [
            ("Market news", search_url("U.S. stock market")),
            ("Trending stocks", search_url("trending stocks")),
            ("ETFs & funds", search_url("ETF mutual fund investing")),
            ("Fund buys", search_url("hedge fund 13F holdings bought stocks")),
        ],
    },
    "india-markets": {
        "title": "India Markets",
        "blurb": "Sensex, Nifty, Indian trending stocks, ETFs and mutual funds.",
        "feeds": [
            ("Market news", search_url("Indian stock market Sensex Nifty", "IN")),
            ("Trending stocks", search_url("trending stocks India", "IN")),
            ("Mutual funds & ETFs", search_url("mutual fund ETF India investing", "IN")),
        ],
    },
    "fidelity": {
        "title": "Fidelity",
        "blurb": "Fidelity Investments — company news, funds, 401(k) and retirement.",
        "feeds": [
            ("Fidelity news", search_url("Fidelity Investments")),
            ("Funds & retirement", search_url("Fidelity 401k retirement funds")),
        ],
    },
    "us-news": {
        "title": "US Headlines",
        "blurb": "Top US national headlines.",
        "feeds": [("Headlines", topic_url("NATION"))],
    },
    "india-news": {
        "title": "India Headlines",
        "blurb": "Top India headlines.",
        "feeds": [("Headlines", topic_url("NATION", "IN"))],
    },
    "kerala": {
        "title": "Kerala",
        "blurb": "Kerala, Kochi, Haripad, Kollam and Alappuzha headlines.",
        "feeds": [
            ("Kerala", search_url("Kerala news", "IN")),
            ("Kochi", search_url("Kochi news", "IN")),
            ("Haripad", search_url("Haripad", "IN")),
            ("Kollam", search_url("Kollam news", "IN")),
            ("Alappuzha", search_url("Alappuzha news", "IN")),
        ],
    },
    "bangalore": {
        "title": "Bangalore",
        "blurb": "Bengaluru headlines — plus North Bengaluru real estate and development.",
        "feeds": [
            ("Bangalore", search_url("Bangalore OR Bengaluru news", "IN")),
            ("North Blr realty", search_url("Bangalore North real estate Devanahalli", "IN")),
            ("North Blr growth", search_url("North Bengaluru development infrastructure projects", "IN")),
        ],
    },
    "airlines": {
        "title": "Airline News",
        "blurb": "Airlines, fares, routes and aviation industry news.",
        "feeds": [
            ("Airlines", search_url("airline industry news")),
            ("Aviation", search_url("aviation news flights routes")),
        ],
    },
    "nc-colleges": {
        "title": "NC Colleges",
        "blurb": "North Carolina college news - for Vybhav's college hunt.",
        "feeds": [
            ("NC colleges", search_url("North Carolina colleges universities")),
            ("UNC news", search_url("UNC Chapel Hill")),
        ],
    },
}


def clean_snippet(raw):
    text = re.sub(r"<[^>]+>", " ", raw or "")
    text = htmlmod.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > 300:
        text = text[:300].rsplit(" ", 1)[0] + "..."
    return text


def fetch_feed(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def parse_items(xml_bytes, feed_label):
    items = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return items
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        if not title or not link:
            continue
        pub = (it.findtext("pubDate") or "").strip()
        try:
            published = parsedate_to_datetime(pub).astimezone(timezone.utc).isoformat()
        except Exception:
            published = ""
        src_el = it.find("source")
        source = src_el.text.strip() if src_el is not None and src_el.text else ""
        snippet = clean_snippet(it.findtext("description"))
        items.append({
            "title": title,
            "link": link,
            "source": source,
            "feed": feed_label,
            "published": published,
            "snippet": snippet,
        })
    return items


def main():
    out = {"fetched_at": datetime.now(timezone.utc).isoformat(), "sections": {}}
    for sec_id, sec in SECTIONS.items():
        seen, merged = set(), []
        for label, url in sec["feeds"]:
            try:
                items = parse_items(fetch_feed(url), label)
            except Exception as e:
                print(f"[{sec_id}] feed '{label}' failed: {e}")
                continue
            for it in items:
                if it["link"] in seen:
                    continue
                seen.add(it["link"])
                merged.append(it)
        merged.sort(key=lambda x: x["published"], reverse=True)
        out["sections"][sec_id] = {
            "title": sec["title"],
            "blurb": sec["blurb"],
            "items": merged[:PER_SECTION_CAP],
        }
        print(f"[{sec_id}] {len(merged[:PER_SECTION_CAP])} items")
    path = os.path.join(DATA_DIR, "raw.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=1)
    print("wrote", path)


if __name__ == "__main__":
    main()
