# scraper/sources/reddit.py

import requests
import time
import hashlib
from bs4 import BeautifulSoup


def scrape_reddit_pullpush():
    """Scrape Reddit via PullPush.io (archive, no API key needed)"""
    
    print("\n" + "=" * 50)
    print("🔍 SCRAPING REDDIT (PullPush)...")
    print("=" * 50)
    
    problems = []
    base_url = "https://api.pullpush.io/reddit/search/submission/"
    
    # Subreddits by category
    subreddit_groups = {
        "startup": ["entrepreneur", "startups", "SaaS", "indiehackers"],
        "small_biz": ["smallbusiness", "ecommerce", "Shopify"],
        "africa": ["Nigeria", "Africa", "Kenya"],
        "money": ["personalfinance", "povertyfinance"],
        "side_hustle": ["sidehustle", "beermoney", "freelance"],
    }
    
    # Pain-indicating search queries
    queries = [
        "frustrated",
        "I hate",
        "looking for alternative",
        "any recommendations",
        "struggling with",
        "waste of money",
        "terrible",
    ]
    
    for category, subreddits in subreddit_groups.items():
        for subreddit in subreddits:
            for query in queries[:4]:  # Limit queries per sub
                try:
                    params = {
                        "subreddit": subreddit,
                        "q": query,
                        "size": 15,
                        "sort_type": "score",
                    }
                    
                    response = requests.get(base_url, params=params, timeout=15)
                    
                    if response.status_code != 200:
                        continue
                    
                    data = response.json()
                    posts = data.get("data", [])
                    
                    for post in posts:
                        if post.get("score", 0) >= 2:
                            title = post.get("title", "")
                            selftext = post.get("selftext", "")
                            post_id = post.get("id", "")
                            
                            problems.append({
                                "source": "Reddit",
                                "subsource": f"r/{subreddit}",
                                "category": category,
                                "title": title[:150],
                                "content": f"{title}\n\n{selftext}"[:800],
                                "score": post.get("score", 0),
                                "comments": post.get("num_comments", 0),
                                "url": f"https://reddit.com{post.get('permalink', '')}",
                                "unique_id": f"rd_{post_id}",
                            })
                    
                    time.sleep(0.4)
                    
                except Exception as e:
                    continue
    
    print(f"   ✅ PullPush: {len(problems)} posts")
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
    
    all_problems.extend(scrape_reddit_pullpush())
    all_problems.extend(scrape_reddit_rss())
    
    print(f"\n   ✅ Reddit Total: {len(all_problems)}")
    return all_problems