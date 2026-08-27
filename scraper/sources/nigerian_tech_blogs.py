# scraper/sources/nigerian_tech_blogs.py

import requests
from bs4 import BeautifulSoup
import time
import hashlib


def scrape_nigerian_tech_blogs():
    """
    Scrape Nigerian tech blog RSS feeds for local market commentary.

    Unlike Reddit/HN (mostly US/global audience), these give Nigeria-specific
    startup, funding, and product-gap commentary that won't show up anywhere
    else in your dataset.
    """

    print("\n" + "=" * 50)
    print("🇳🇬 SCRAPING NIGERIAN TECH BLOGS...")
    print("=" * 50)

    problems = []

    feeds = [
        ("Techpoint Africa", "https://techpoint.africa/feed/"),
        ("TechCabal", "https://techcabal.com/feed/"),
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
    }

    for blog_name, feed_url in feeds:
        try:
            response = requests.get(feed_url, headers=headers, timeout=15)

            if response.status_code != 200:
                print(f"   ⚠️ {blog_name}: HTTP {response.status_code}")
                continue

            soup = BeautifulSoup(response.text, 'xml')
            items = soup.find_all('item')

            count = 0
            for item in items[:40]:
                title_elem = item.find('title')
                link_elem = item.find('link')
                desc_elem = item.find('description')

                title = title_elem.text.strip() if title_elem else ''
                link = link_elem.text.strip() if link_elem else ''
                description = desc_elem.text.strip() if desc_elem else ''

                if not title:
                    continue

                # Strip any HTML in the description
                clean_desc = BeautifulSoup(description, 'html.parser').get_text()

                problems.append({
                    "source": "NigerianTechBlog",
                    "subsource": blog_name,
                    "title": title[:150],
                    "content": f"{title}\n\n{clean_desc}"[:600],
                    "score": 0,
                    "url": link,
                    "unique_id": f"ntb_{hashlib.md5(link.encode()).hexdigest()[:12]}",
                })
                count += 1

            print(f"   📌 {blog_name}: {count} articles")
            time.sleep(1)

        except Exception as e:
            print(f"   ❌ {blog_name}: {type(e).__name__}: {e}")
            continue

    print(f"\n   ✅ Nigerian Tech Blogs Total: {len(problems)}")
    return problems
