# scraper/sources/trends.py

import requests
from bs4 import BeautifulSoup
import time


def _parse_trends_rss(geo: str, subsource: str, max_items: int = 20):
    """
    Parse Google's public daily-trending-searches RSS feed for a given geo.

    Replaces the old pytrends-based scraper: pytrends was archived upstream
    in April 2025 and its trending_searches() call now 404s, so it was
    silently returning nothing. This feed is public, needs no API key, and
    exposes the top ~20 daily trends per country plus related news context.
    """

    trends = []
    url = f"https://trends.google.com/trending/rss?geo={geo}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            print(f"   ⚠️ {subsource} trends failed: HTTP {response.status_code}")
            return trends

        soup = BeautifulSoup(response.text, 'lxml-xml')
        items = soup.find_all('item')[:max_items]

        for idx, item in enumerate(items):
            title_elem = item.find('title')
            title = title_elem.text.strip() if title_elem else ''

            if not title:
                continue

            # approx_traffic is a Google-Trends-namespaced field, e.g. "5000+"
            traffic_elem = item.find('ht:approx_traffic') or item.find('approx_traffic')
            traffic_text = traffic_elem.text.strip() if traffic_elem else ''

            # Related news gives useful context on *why* something is trending
            news_title_elem = item.find('ht:news_item_title') or item.find('news_item_title')
            news_snippet_elem = item.find('ht:news_item_snippet') or item.find('news_item_snippet')

            content_parts = [title]
            if traffic_text:
                content_parts.append(f"Search volume signal: {traffic_text}")
            if news_title_elem:
                content_parts.append(f"Related news: {news_title_elem.text.strip()}")
            if news_snippet_elem:
                content_parts.append(news_snippet_elem.text.strip()[:200])

            trends.append({
                "source": "GoogleTrends",
                "subsource": subsource,
                "title": title[:150],
                "content": " | ".join(content_parts)[:600],
                "score": max(0, 100 - idx * 3),  # simple recency/rank-based score
                "url": f"https://trends.google.com/trends/explore?q={title.replace(' ', '+')}",
                "unique_id": f"gt_{geo.lower()}_{idx}_{title[:20]}",
            })

        print(f"   ✅ {subsource} trends: {len(trends)}")

    except Exception as e:
        print(f"   ⚠️ {subsource} trends failed: {type(e).__name__}: {e}")

    return trends


def scrape_google_trends():
    """Get trending searches from Google Trends' public RSS feed (NG + US)"""

    print("\n" + "=" * 50)
    print("📈 SCRAPING GOOGLE TRENDS...")
    print("=" * 50)

    trends = []

    trends.extend(_parse_trends_rss(geo="NG", subsource="Nigeria"))
    time.sleep(1)
    trends.extend(_parse_trends_rss(geo="US", subsource="Global"))

    return trends


def scrape_all_trends():
    """Combine all trend sources"""

    all_trends = []
    all_trends.extend(scrape_google_trends())

    print(f"\n   ✅ Trends Total: {len(all_trends)}")
    return all_trends