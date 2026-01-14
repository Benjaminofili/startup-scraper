# scraper/sources/reddit.py

import requests
import time
import os

# Multiple Reddit access methods (fallbacks)


def scrape_reddit_pullpush():
    """Method 1: PullPush.io (Reddit archive - always works)"""
    
    print("\n" + "="*50)
    print("🔍 REDDIT VIA PULLPUSH...")
    print("="*50)
    
    problems = []
    base_url = "https://api.pullpush.io/reddit/search/submission/"
    
    # Subreddits by category
    subreddit_groups = {
        "startup": ["entrepreneur", "startups", "SaaS", "indiehackers", "microsaas"],
        "side_hustle": ["sidehustle", "beermoney", "WorkOnline", "freelance"],
        "small_biz": ["smallbusiness", "ecommerce", "dropship", "shopify"],
        "africa": ["Nigeria", "Lagos", "Africa", "Kenya", "SouthAfrica"],
        "students": ["college", "GradSchool", "cscareerquestions"],
        "money": ["personalfinance", "povertyfinance", "FinancialPlanning"],
    }
    
    # Pain-indicating phrases
    queries = [
        "frustrated with",
        "I hate",
        "looking for alternative",
        "is there an app",
        "why is it so hard",
        "any recommendations",
        "help me find",
        "struggling with",
        "waste of money",
        "terrible experience",
    ]
    
    for category, subreddits in subreddit_groups.items():
        for subreddit in subreddits:
            for query in queries[:5]:  # Limit queries per subreddit
                try:
                    params = {
                        "subreddit": subreddit,
                        "q": query,
                        "size": 15,
                        "sort_type": "score",
                        "after": "30d"  # Last 30 days
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
                            
                            problems.append({
                                "source": "Reddit",
                                "subsource": f"r/{subreddit}",
                                "category": category,
                                "title": title[:150],
                                "content": f"{title}\n\n{selftext}"[:800],
                                "score": post.get("score", 0),
                                "comments": post.get("num_comments", 0),
                                "url": f"https://reddit.com{post.get('permalink', '')}",
                                "unique_id": f"rd_{post.get('id', '')}",
                                "date": "",
                            })
                    
                    time.sleep(0.3)
                    
                except Exception as e:
                    continue
    
    print(f"   ✅ PullPush: {len(problems)} posts")
    return problems


def scrape_reddit_arctic():
    """Method 2: Arctic Shift (another Reddit archive)"""
    
    print("\n   🔍 REDDIT VIA ARCTIC SHIFT...")
    
    problems = []
    base_url = "https://arctic-shift.photon-reddit.com/api/posts"
    
    subreddits = ["entrepreneur", "startups", "smallbusiness"]
    
    for subreddit in subreddits:
        try:
            params = {
                "subreddit": subreddit,
                "limit": 50,
                "sort": "score"
            }
            
            response = requests.get(base_url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                posts = data.get("data", [])
                
                for post in posts:
                    if post.get("score", 0) >= 5:
                        problems.append({
                            "source": "Reddit",
                            "subsource": f"r/{subreddit}",
                            "title": post.get("title", "")[:150],
                            "content": post.get("selftext", "")[:600],
                            "score": post.get("score", 0),
                            "url": f"https://reddit.com/r/{subreddit}/comments/{post.get('id', '')}",
                            "unique_id": f"arc_{post.get('id', '')}",
                        })
                        
            time.sleep(0.5)
            
        except Exception as e:
            continue
    
    print(f"   ✅ Arctic Shift: {len(problems)} posts")
    return problems


def scrape_reddit_rss():
    """Method 3: Reddit RSS feeds (no auth needed, real-time)"""
    
    print("\n   🔍 REDDIT VIA RSS...")
    
    from bs4 import BeautifulSoup
    
    problems = []
    
    # RSS feeds work without authentication
    feeds = [
        "https://www.reddit.com/r/entrepreneur/new/.rss?limit=50",
        "https://www.reddit.com/r/startups/new/.rss?limit=50",
        "https://www.reddit.com/r/SaaS/new/.rss?limit=50",
        "https://www.reddit.com/r/smallbusiness/new/.rss?limit=50",
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
                    title = entry.find('title').text if entry.find('title') else ""
                    content = entry.find('content').text if entry.find('content') else ""
                    link = entry.find('link')['href'] if entry.find('link') else ""
                    entry_id = entry.find('id').text if entry.find('id') else ""
                    
                    # Filter for problem-related posts
                    combined = (title + content).lower()
                    if any(kw in combined for kw in problem_keywords):
                        problems.append({
                            "source": "Reddit",
                            "subsource": f"r/{subreddit}",
                            "title": title[:150],
                            "content": BeautifulSoup(content, 'html.parser').get_text()[:500],
                            "score": 0,
                            "url": link,
                            "unique_id": f"rss_{hashlib.md5(entry_id.encode()).hexdigest()[:12]}",
                        })
                        
            time.sleep(0.5)
            
        except Exception as e:
            continue
    
    print(f"   ✅ RSS: {len(problems)} posts")
    return problems


def scrape_reddit_all():
    """Combine all Reddit methods"""
    
    import hashlib
    
    all_problems = []
    
    # Try all methods
    all_problems.extend(scrape_reddit_pullpush())
    all_problems.extend(scrape_reddit_arctic())
    all_problems.extend(scrape_reddit_rss())
    
    print(f"\n   ✅ Reddit Total: {len(all_problems)}")
    return all_problems