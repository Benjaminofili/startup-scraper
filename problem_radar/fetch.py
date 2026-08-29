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

import json
import os
import time
from datetime import datetime, timezone

import requests

OUT_PATH = os.path.join(os.path.dirname(__file__), "data", "corpus.json")

# Matches scraper/sources/reddit.py's proven-working User-Agent. Reddit is
# picky about generic/unfamiliar UA strings (silently 403s/429s), so this
# isn't a place to improvise a new one.
REDDIT_HEADERS = {"User-Agent": "StartupScraper/1.0 (by /u/your_reddit_username)"}

# Same subreddit pool the live Reddit source draws from, but every entry
# gets queried here instead of a rotated slice - this run is meant to be
# a single broad snapshot, not an incremental daily sample.
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

# Kept short deliberately - each query fans out across every subreddit
# above, so keeping this list small is what keeps total request count
# (subreddits x queries) manageable.
REDDIT_QUERIES = ["frustrated", "wish there was", "looking for alternative", "waste of money"]

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
    base_url = "https://old.reddit.com/r/{subreddit}/search.json"

    for subreddit in SUBREDDITS:
        for query in REDDIT_QUERIES:
            try:
                params = {"q": query, "restrict_sr": 1, "sort": "top", "t": "year", "limit": 15}
                resp = requests.get(
                    base_url.format(subreddit=subreddit),
                    headers=REDDIT_HEADERS, params=params, timeout=15,
                )
                status_counts[resp.status_code] = status_counts.get(resp.status_code, 0) + 1
                if resp.status_code == 429:
                    print(f"  rate limited on r/{subreddit}, backing off")
                    time.sleep(5)
                    continue
                if resp.status_code != 200:
                    print(f"  r/{subreddit} '{query}': HTTP {resp.status_code}")
                    continue

                for post in resp.json().get("data", {}).get("children", []):
                    p = post.get("data", {})
                    if p.get("score", 0) < 2:
                        continue
                    title = p.get("title", "")
                    selftext = p.get("selftext", "")
                    docs.append({
                        "doc_id": f"reddit_{p.get('id', '')}",
                        "source": "Reddit",
                        "subsource": f"r/{subreddit}",
                        "author": p.get("author", ""),
                        "title": title[:200],
                        "content": f"{title}\n\n{selftext}"[:1000],
                        "score": p.get("score", 0),
                        "comments": p.get("num_comments", 0),
                        "url": f"https://reddit.com{p.get('permalink', '')}",
                        "created_utc": p.get("created_utc"),
                    })
                time.sleep(1.2)
            except Exception as e:
                print(f"  r/{subreddit} '{query}': {type(e).__name__}: {e}")
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
                docs.append({
                    "doc_id": f"hn_{object_id}",
                    "source": "HackerNews",
                    "subsource": "search",
                    "author": hit.get("author", ""),
                    "title": title[:200],
                    "content": title,
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
