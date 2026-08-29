# problem_radar/fetch.py
"""
Standalone corpus fetcher for the Problem Radar experiment.

Deliberately separate from scraper/sources/*.py: those feed the live
scheduled pipeline (scraper.main) and share rotation/seen-id state in
data/rotation_state.json and data/seen_ids.json. This script must not
touch that state - it pulls a single wide snapshot from Reddit + Hacker
News in one pass, dedupes it locally, and writes it to its own file
under problem_radar/data/. Nothing here is scheduled or wired into the
production scrape.

Usage:
    python -m problem_radar.fetch
"""

import hashlib
import json
import os
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

OUT_PATH = os.path.join(os.path.dirname(__file__), "data", "corpus.json")

# old.reddit.com/search.json 403s every request from GitHub Actions
# runners (confirmed empirically - run #2 got HTTP 403 on all 80
# requests; see the Problem Radar experiment history for details). Its
# straight RSS feeds don't get the same treatment, so that's the method
# used here - same one scraper/sources/reddit.py falls back to. Browser
# UA matters more than an honest one for this endpoint in practice.
REDDIT_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}

# Same subreddit pool the live Reddit source draws from. RSS feeds are a
# fixed recent/top listing, not a search - there's no per-query fan-out
# here, just one feed per subreddit.
SUBREDDITS = [
    "entrepreneur", "startups", "SaaS", "indiehackers",
    "smallbusiness", "ecommerce", "Shopify",
    "Nigeria", "Africa", "Kenya",
    "personalfinance", "povertyfinance",
    "sidehustle", "freelance",
    "mildlyinfuriating", "software",
    "BuyItForLife", "consumeradvice",
    "productivity", "getdisciplined",
]

HN_QUERIES = [
    "startup idea", "I built", "frustrating", "alternative to",
    "looking for a tool", "does anyone know a tool",
    "why is there no", "wish there was an app",
    "I wasted money on", "hate paying for",
    "side project revenue", "indie hacker",
    "built this because", "solo founder",
    "underrated problem", "nobody has solved",
    "show hn i made", "ask hn recommend",
    "switched away from", "cancelled my subscription",
    "manual process", "spreadsheet hell",
    "small business owner", "freelancer struggling",
    "open source alternative", "self-hosted",
    "burned out on", "too expensive for what it does",
    "customer support nightmare", "onboarding was confusing",
]


def fetch_reddit():
    print("Fetching Reddit...")
    docs = []
    status_counts = {}

    for subreddit in SUBREDDITS:
        for sort_path in ("top/.rss?t=year&limit=40", "new/.rss?limit=25"):
            feed_url = f"https://www.reddit.com/r/{subreddit}/{sort_path}"
            try:
                resp = requests.get(feed_url, headers=REDDIT_HEADERS, timeout=15)
                status_counts[resp.status_code] = status_counts.get(resp.status_code, 0) + 1
                if resp.status_code != 200:
                    print(f"  r/{subreddit} ({sort_path.split('/')[0]}): HTTP {resp.status_code}")
                    continue

                soup = BeautifulSoup(resp.text, "lxml-xml")
                for entry in soup.find_all("entry"):
                    title_el = entry.find("title")
                    content_el = entry.find("content")
                    link_el = entry.find("link")
                    author_el = entry.find("author")

                    title = title_el.text if title_el else ""
                    if not title:
                        continue
                    raw_content = content_el.text if content_el else ""
                    body = BeautifulSoup(raw_content, "html.parser").get_text(" ", strip=True)
                    link = link_el["href"] if link_el and link_el.has_attr("href") else ""
                    author = author_el.find("name").text if author_el and author_el.find("name") else ""

                    doc_id = f"reddit_{hashlib.md5(link.encode()).hexdigest()[:12]}" if link else None
                    if not doc_id:
                        continue

                    docs.append({
                        "doc_id": doc_id,
                        "source": "Reddit",
                        "subsource": f"r/{subreddit}",
                        "author": author,
                        "title": title[:200],
                        "content": f"{title}\n\n{body}"[:1000],
                        "score": 0,
                        "comments": 0,
                        "url": link,
                        "created_utc": None,
                    })
                time.sleep(1.0)
            except Exception as e:
                print(f"  r/{subreddit} ({sort_path.split('/')[0]}): {type(e).__name__}: {e}")
                continue

    print(f"  Reddit: {len(docs)} raw docs (status codes: {status_counts})")
    return docs


def fetch_hackernews():
    print("Fetching Hacker News...")
    docs = []
    search_url = "https://hn.algolia.com/api/v1/search"
    six_months_ago = int(time.time()) - (60 * 60 * 24 * 180)

    for query in HN_QUERIES:
        try:
            params = {
                "query": query,
                "tags": "story",
                "hitsPerPage": 20,
                "numericFilters": f"created_at_i>{six_months_ago}",
            }
            resp = requests.get(search_url, params=params, timeout=10)
            if resp.status_code != 200:
                continue
            for hit in resp.json().get("hits", []):
                object_id = hit.get("objectID", "")
                title = hit.get("title") or hit.get("story_title") or ""
                if not object_id or not title:
                    continue
                # Link posts have no body; Ask/Show HN posts often do
                # (story_text) - include it when present, it's the
                # difference between "some title" and actual complaint
                # text for the embedding to work with.
                body = hit.get("story_text") or ""
                if body:
                    body = BeautifulSoup(body, "html.parser").get_text(" ", strip=True)
                docs.append({
                    "doc_id": f"hn_{object_id}",
                    "source": "HackerNews",
                    "subsource": "search",
                    "author": hit.get("author", ""),
                    "title": title[:200],
                    "content": f"{title}\n\n{body}"[:1000] if body else title,
                    "score": hit.get("points", 0),
                    "comments": hit.get("num_comments", 0),
                    "url": f"https://news.ycombinator.com/item?id={object_id}",
                    "created_utc": hit.get("created_at_i"),
                })
            time.sleep(0.3)
        except Exception as e:
            print(f"  HN '{query}': {type(e).__name__}: {e}")
            continue

    print(f"  Hacker News: {len(docs)} raw docs")
    return docs


def dedupe(docs):
    seen = set()
    out = []
    for d in docs:
        if d["doc_id"] in seen:
            continue
        seen.add(d["doc_id"])
        out.append(d)
    return out


def main():
    docs = dedupe(fetch_reddit() + fetch_hackernews())
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    corpus = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "total_docs": len(docs),
        "sources": {
            src: sum(1 for d in docs if d["source"] == src)
            for src in sorted({d["source"] for d in docs})
        },
        "docs": docs,
    }
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(corpus, f, indent=2)

    print(f"\nWrote {len(docs)} deduped docs -> {OUT_PATH}")
    print(f"Sources: {corpus['sources']}")


if __name__ == "__main__":
    main()
