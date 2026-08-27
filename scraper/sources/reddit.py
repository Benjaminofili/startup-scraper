# scraper/sources/reddit.py

import requests
import time
import hashlib
from bs4 import BeautifulSoup


def scrape_reddit_search():
    """
    Scrape Reddit via Reddit's own public search.json endpoint.

    Replaces the old PullPush.io scraper: PullPush now returns a paid-only
    rate-limit error for any automated/agent traffic ("This website does
    not provide free scraping resources for agents"), so it was
    contributing nothing for however long it's been that way. Reddit's own
    old.reddit.com search.json endpoint is still free and unauthenticated,
    it just needs a real User-Agent and slower pacing to avoid 429s.
    """

    print("\n" + "=" * 50)
    print("🔍 SCRAPING REDDIT (search.json)...")
    print("=" * 50)

    problems = []
    base_url = "https://old.reddit.com/r/{subreddit}/search.json"

    headers = {
        "User-Agent": "StartupScraper/1.0 (by /u/your_reddit_username)"
    }

    subreddit_pool = {
        "startup": ["entrepreneur", "startups", "SaaS", "indiehackers"],
        "small_biz": ["smallbusiness", "ecommerce", "Shopify"],
        "africa": ["Nigeria", "Africa", "Kenya"],
        "money": ["personalfinance", "povertyfinance"],
        "side_hustle": ["sidehustle", "beermoney", "freelance"],
        "tech_frustration": ["mildlyinfuriating", "assholedesign", "software"],
        "consumer": ["ShouldIbuythisgame", "BuyItForLife", "consumeradvice"],
        "productivity": ["productivity", "getdisciplined", "organization"],
    }

    query_pool = [
        "frustrated",
        "I hate",
        "looking for alternative",
        "any recommendations",
        "struggling with",
        "waste of money",
        "terrible",
        "wish there was",
        "does this exist",
        "switched from",
    ]

    from scraper.utils.state_tracker import get_rotation_slice

    # Flatten the subreddit pool into (category, subreddit) pairs and take
    # a rotating slice, so successive scheduled runs sample different
    # subreddits instead of hitting the same 15 every single time.
    flat_subs = [(cat, sub) for cat, subs in subreddit_pool.items() for sub in subs]
    rotated_subs = get_rotation_slice(flat_subs, chunk_size=10, state_key="reddit_subs")
    queries = get_rotation_slice(query_pool, chunk_size=4, state_key="reddit_queries")

    for category, subreddit in rotated_subs:
        for query in queries:
                try:
                    params = {
                        "q": query,
                        "restrict_sr": 1,
                        "sort": "top",
                        "t": "year",
                        "limit": 15,
                    }

                    response = requests.get(
                        base_url.format(subreddit=subreddit),
                        headers=headers,
                        params=params,
                        timeout=15,
                    )

                    if response.status_code == 429:
                        print(f"   ⏳ Rate limited on r/{subreddit}, backing off")
                        time.sleep(5)
                        continue

                    if response.status_code != 200:
                        print(f"   ⚠️ r/{subreddit} '{query}': HTTP {response.status_code}")
                        continue

                    data = response.json()
                    posts = data.get("data", {}).get("children", [])

                    for post in posts:
                        p = post.get("data", {})
                        if p.get("score", 0) >= 2:
                            title = p.get("title", "")
                            selftext = p.get("selftext", "")
                            post_id = p.get("id", "")

                            problems.append({
                                "source": "Reddit",
                                "subsource": f"r/{subreddit}",
                                "category": category,
                                "title": title[:150],
                                "content": f"{title}\n\n{selftext}"[:800],
                                "score": p.get("score", 0),
                                "comments": p.get("num_comments", 0),
                                "url": f"https://reddit.com{p.get('permalink', '')}",
                                "unique_id": f"rd_{post_id}",
                            })

                    time.sleep(1.2)  # Reddit rate-limits harder than PullPush did

                except Exception as e:
                    print(f"   ⚠️ r/{subreddit} '{query}': {type(e).__name__}: {e}")
                    continue

    print(f"   ✅ Reddit search: {len(problems)} posts")
    return problems


def scrape_reddit_rss():
    """Scrape Reddit via RSS (backup method, real-time)"""
    
    print("\n   🔄 Trying Reddit RSS...")
    
    problems = []
    
    feeds = [
        "https://www.reddit.com/r/entrepreneur/new/.rss?limit=30",
        "https://www.reddit.com/r/startups/new/.rss?limit=30",
        "https://www.reddit.com/r/smallbusiness/new/.rss?limit=30",
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
    }
    
    problem_keywords = ['help', 'frustrated', 'looking for', 'recommend',
                        'alternative', 'struggling', 'hate', 'issue', 'problem']
    
    for feed_url in feeds:
        try:
            response = requests.get(feed_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'lxml-xml')
                entries = soup.find_all('entry')
                
                subreddit = feed_url.split('/r/')[1].split('/')[0]
                
                for entry in entries:
                    title_elem = entry.find('title')
                    content_elem = entry.find('content')
                    link_elem = entry.find('link')
                    
                    title = title_elem.text if title_elem else ""
                    content = content_elem.text if content_elem else ""
                    link = link_elem['href'] if link_elem else ""
                    
                    # Filter for problem-related posts
                    combined = (title + content).lower()
                    if any(kw in combined for kw in problem_keywords):
                        # Clean HTML from content
                        clean_content = BeautifulSoup(content, 'html.parser').get_text()
                        
                        problems.append({
                            "source": "Reddit",
                            "subsource": f"r/{subreddit}",
                            "title": title[:150],
                            "content": clean_content[:500],
                            "score": 0,
                            "url": link,
                            "unique_id": f"rss_{hashlib.md5(link.encode()).hexdigest()[:12]}",
                        })
                        
            time.sleep(0.5)
            
        except Exception as e:
            continue
    
    print(f"   ✅ RSS: {len(problems)} posts")
    return problems


def scrape_reddit_all():
    """Combine all Reddit scraping methods"""
    
    all_problems = []
    
    all_problems.extend(scrape_reddit_search())
    all_problems.extend(scrape_reddit_rss())
    
    print(f"\n   ✅ Reddit Total: {len(all_problems)}")
    return all_problems