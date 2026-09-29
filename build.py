#!/usr/bin/env python3
"""news.ai builder - render data/raw.json (+ evergreen pages) into site/.

Run: python3 build.py (after fetch.py)
"""
import html as htmlmod
import json
import os
import shutil
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")
SITE_DIR = os.path.join(BASE, "site")
STATIC_DIR = os.path.join(BASE, "static")
ET = ZoneInfo("America/New_York")

SECTIONS_ORDER = [
    ("immigration", "Immigration: EB-1 & L-1A"),
    ("ai-tech", "AI & Technology"),
    ("us-markets", "US Markets"),
    ("india-markets", "India Markets"),
    ("fidelity", "Fidelity"),
    ("us-news", "US Headlines"),
    ("india-news", "India Headlines"),
    ("kerala", "Kerala"),
    ("bangalore", "Bangalore"),
    ("airlines", "Airline News"),
    ("nc-colleges", "NC Colleges"),
]

NAV = "".join(
    f'<a href="{sid}.html">{htmlmod.escape(title)}</a>'
    for sid, title in SECTIONS_ORDER
)

BASE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} &middot; news.ai</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<header>
  <div class="wrap bar">
    <a class="brand" href="index.html">news<span>.ai</span></a>
    <span class="updated">Updated {updated}</span>
  </div>
  <nav class="wrap">{nav}</nav>
</header>
<main class="wrap">
{body}
</main>
<footer class="wrap">
  <p>Headlines via Google News RSS &middot; links open the original publishers &middot; auto-refreshed hourly</p>
</footer>
</body>
</html>
"""

CAROUSEL_JS = """<script>
(function () {
  function perView() {
    return window.innerWidth < 640 ? 1 : window.innerWidth < 1024 ? 2 : 4;
  }
  document.querySelectorAll(".carousel").forEach(function (car) {
    var track = car.querySelector(".track");
    var slides = track.children;
    var total = slides.length;
    if (!total) return;
    var scope = car.closest("section") || car.parentElement;
    var pager = scope.querySelector(".pager");
    if (!pager) return;
    var prev = pager.querySelector(".prev");
    var next = pager.querySelector(".next");
    var dots = pager.querySelector(".dots");
    var page = 0, timer = null;
    function pages() { return Math.max(1, Math.ceil(total / perView())); }
    function render() {
      var pv = perView(), p = pages();
      if (page > p - 1) page = p - 1;
      for (var i = 0; i < total; i++) slides[i].style.flexBasis = 100 / pv + "%";
      track.style.transform = "translateX(" + -page * 100 + "%)";
      dots.innerHTML = "";
      for (var d = 0; d < p; d++) {
        (function (d) {
          var b = document.createElement("button");
          b.className = "dot" + (d === page ? " on" : "");
          b.setAttribute("aria-label", "Go to page " + (d + 1));
          b.addEventListener("click", function () { page = d; render(); restart(); });
          dots.appendChild(b);
        })(d);
      }
      prev.disabled = page === 0;
      next.disabled = page === p - 1;
      pager.style.display = p <= 1 ? "none" : "";
    }
    function restart() {
      if (timer) clearInterval(timer);
      if (pages() > 1) {
        timer = setInterval(function () { page = (page + 1) % pages(); render(); }, 9000);
      }
    }
    prev.addEventListener("click", function () { if (page > 0) { page--; render(); restart(); } });
    next.addEventListener("click", function () { if (page < pages() - 1) { page++; render(); restart(); } });
    car.addEventListener("pointerenter", function () { if (timer) clearInterval(timer); });
    car.addEventListener("pointerleave", restart);
    window.addEventListener("resize", render);
    render();
    restart();
  });
})();
</script>"""


def esc(s):
    return htmlmod.escape(s or "")


def time_ago(iso):
    try:
        dt = datetime.fromisoformat(iso)
    except Exception:
        return ""
    mins = max(0, int((datetime.now(timezone.utc) - dt).total_seconds() // 60))
    if mins < 60:
        return f"{mins}m ago"
    hrs = mins // 60
    if hrs < 24:
        return f"{hrs}h ago"
    return f"{hrs // 24}d ago"


def card(it):
    meta = " &middot; ".join(esc(p) for p in [it["source"], it["feed"], time_ago(it["published"])] if p)
    snippet = f"<p>{esc(it['snippet'])}</p>" if it.get("snippet") else ""
    return (
        '<article class="card">\n'
        f'  <h3><a href="{esc(it["link"])}" target="_blank" rel="noopener">{esc(it["title"])}</a></h3>\n'
        f'  <div class="meta">{meta}</div>\n'
        f'  {snippet}\n'
        "</article>"
    )


PAGER = (
    '<div class="pager">'
    '<button class="pg prev" aria-label="Previous stories">&#8249;</button>'
    '<span class="dots"></span>'
    '<button class="pg next" aria-label="Next stories">&#8250;</button>'
    "</div>"
)


def carousel(items):
    slides = "\n".join(f'<div class="slide">{card(it)}</div>' for it in items)
    return f'<div class="carousel"><div class="track">\n{slides}\n</div></div>'


def render_page(title, updated, body):
    return BASE_HTML.format(title=esc(title), updated=esc(updated), nav=NAV, body=body) + CAROUSEL_JS


def colleges_body(raw):
    path = os.path.join(DATA_DIR, "nc_colleges.json")
    try:
        with open(path) as f:
            guide = json.load(f)
    except Exception:
        guide = {"intro": "", "colleges": []}
    parts = ["<h1>NC Colleges</h1>",
             f'<p class="blurb">{esc(guide.get("intro", ""))}</p>',
             '<div class="guide">']
    for c in guide.get("colleges", []):
        links = " &middot; ".join(
            f'<a href="{esc(u)}" target="_blank" rel="noopener">{esc(name)}</a>'
            for name, u in c.get("links", {}).items()
        )
        parts.append(
            '<article class="card">'
            f'<h3>{esc(c["name"])}</h3>'
            f'<div class="meta">{esc(c.get("meta", ""))}</div>'
            f'<p>{esc(c.get("note", ""))}</p>'
            + (f'<div class="meta">{links}</div>' if links else "")
            + "</article>"
        )
    parts.append(f'</div><div class="sec-head"><h2>Latest NC college news</h2><div class="sec-tools">{PAGER}</div></div>')
    sec = raw["sections"].get("nc-colleges", {})
    items = sec.get("items", [])
    parts.append(carousel(items) if items else '<p class="empty">No fresh stories this hour.</p>')
    return "\n".join(parts)


def main():
    with open(os.path.join(DATA_DIR, "raw.json")) as f:
        raw = json.load(f)
    try:
        updated = datetime.fromisoformat(raw["fetched_at"]).astimezone(ET).strftime("%b %d, %I:%M %p ET")
    except Exception:
        updated = raw.get("fetched_at", "")

    os.makedirs(SITE_DIR, exist_ok=True)

    blocks = []
    for sid, title in SECTIONS_ORDER:
        sec = raw["sections"].get(sid, {})
        items = sec.get("items", [])[:12]
        cards = carousel(items) if items else '<p class="empty">No fresh stories this hour.</p>'
        blocks.append(
            '<section class="sec">\n'
            f'  <div class="sec-head"><h2>{esc(title)}</h2>'
            f'<div class="sec-tools">{PAGER}<a class="more" href="{sid}.html">More &rarr;</a></div></div>\n'
            f'  <p class="blurb">{esc(sec.get("blurb", ""))}</p>\n'
            f"  {cards}\n</section>"
        )
    index_body = (
        '<div class="hero"><h1>Your hourly briefing</h1>'
        "<p>EB-1 &amp; L-1A watch, AI, US &amp; India markets, Fidelity, Kerala wires, airlines, "
        "and NC colleges &mdash; refreshed every hour.</p></div>\n"
        + "\n".join(blocks)
    )
    with open(os.path.join(SITE_DIR, "index.html"), "w") as f:
        f.write(render_page("Home", updated, index_body))

    for sid, title in SECTIONS_ORDER:
        if sid == "nc-colleges":
            body = colleges_body(raw)
        else:
            sec = raw["sections"].get(sid, {})
            items = sec.get("items", [])
            body = (f'<div class="sec-head"><h1>{esc(title)}</h1><div class="sec-tools">{PAGER}</div></div>\n'
                    f'<p class="blurb">{esc(sec.get("blurb", ""))}</p>\n'
                    + (carousel(items) if items else '<p class="empty">No fresh stories this hour.</p>'))
        with open(os.path.join(SITE_DIR, f"{sid}.html"), "w") as f:
            f.write(render_page(title, updated, body))

    shutil.copy(os.path.join(STATIC_DIR, "style.css"), os.path.join(SITE_DIR, "style.css"))
    print("site written to", SITE_DIR)


if __name__ == "__main__":
    main()
