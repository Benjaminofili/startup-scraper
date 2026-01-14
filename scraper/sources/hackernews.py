# scraper/sources/hackernews.py

import requests
import time

def scrape_hackernews():
    """Scrape Hacker News - free API, no auth needed"""
    
    print("\n" + "="*50)
    print("🔶 SCRAPING HACKER NEWS...")
    print("="*50)
    
    problems = []
    
    # HN API endpoints
    base_url = "https://hacker-news.firebaseio.com/v0"
    
    # Get different story types
    story_types = ['topstories', 'newstories', 'askstories', 'showstories']
    
    problem_keywords = [
        'frustrated', 'hate', 'broken', 'alternative', 'looking for',
        'recommend', 'help', 'struggle', 'problem', 'issue', 'wish',
        'anyone built', 'is there', 'why is', 'how do you'
    ]
    
    for story_type in story_types:
        try:
            # Get story IDs
            response = requests.get(f"{base_url}/{story_type}.json", timeout=10)
            story_ids = response.json()[:100]  # Top 100
            
            print(f"   📌 Checking {story_type}...")
            
            for story_id in story_ids[:50]:  # Process 50 per type
                try:
                    item = requests.get(f"{base_url}/item/{story_id}.json", timeout=5).json()
                    
                    if not item:
                        continue
                    
                    title = item.get('title', '')
                    text = item.get('text', '') or ''
                    score = item.get('score', 0)
                    
                    # Filter for problem-related content
                    combined = (title + text).lower()
                    
                    if any(kw in combined for kw in problem_keywords) or score > 100:
                        problems.append({
                            "source": "HackerNews",
                            "subsource": story_type,
                            "title": title[:150],
                            "content": f"{title}\n\n{text}"[:600],
                            "score": score,
                            "comments": item.get('descendants', 0),
                            "url": item.get('url', f"https://news.ycombinator.com/item?id={story_id}"),
                            "unique_id": f"hn_{story_id}",
                            "date": "",
                        })
                    
                    time.sleep(0.1)
                    
                except Exception:
                    continue
                    
        except Exception as e:
            print(f"   ❌ {story_type}: {e}")
            continue
    
    # Also search for specific topics
    search_url = "https://hn.algolia.com/api/v1/search"
    
    search_queries = [
        "startup idea",
        "I built",
        "looking for cofounders",
        "frustrating",
        "wish there was",
        "alternative to"
    ]
    
    print("   📌 Searching HN...")
    
    for query in search_queries:
        try:
            params = {"query": query, "tags": "story", "hitsPerPage": 20}
            response = requests.get(search_url, params=params, timeout=10)
            
            if response.status_code == 200:
                hits = response.json().get('hits', [])
                
                for hit in hits:
                    problems.append({
                        "source": "HackerNews",
                        "subsource": "search",
                        "title": hit.get('title', '')[:150],
                        "content": hit.get('title', ''),
                        "score": hit.get('points', 0),
                        "comments": hit.get('num_comments', 0),
                        "url": f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
                        "unique_id": f"hns_{hit.get('objectID', '')}",
                    })
                    
            time.sleep(0.3)
            
        except Exception:
            continue
    
    print(f"\n   ✅ Hacker News Total: {len(problems)}")
    return problems