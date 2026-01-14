# scraper/sources/twitter.py
"""
⚠️ LEGAL WARNING ⚠️

Twitter/X explicitly prohibits scraping in their Terms of Service.
They have sued companies for scraping (hiQ Labs case, 2022).

This file is provided for EDUCATIONAL PURPOSES ONLY.
Using this in production may result in:
- IP bans
- Legal action from Twitter/X
- Account suspension

SAFER ALTERNATIVES:
1. Use Twitter API v2 (requires approval, has free tier)
2. Use social listening tools (Brandwatch, Mention)
3. Skip Twitter entirely - Reddit/HN have similar data

If you choose to use this, you do so at YOUR OWN RISK.
"""

import os
import requests
from bs4 import BeautifulSoup
import time

# Check for explicit opt-in
ENABLE_TWITTER_SCRAPING = os.getenv("ENABLE_TWITTER_SCRAPING", "false").lower() == "true"


def scrape_twitter_nitter():
    """
    Scrape Twitter via Nitter instances.
    Disabled by default for legal safety.
    """
    
    if not ENABLE_TWITTER_SCRAPING:
        print("\n   ⚠️ Twitter scraping disabled (legal concerns)")
        print("   Set ENABLE_TWITTER_SCRAPING=true to enable at your own risk")
        return []
    
    print("\n" + "="*50)
    print("🐦 SCRAPING TWITTER (at your own risk)...")
    print("="*50)


def scrape_twitter_nitter():
    """Scrape Twitter via Nitter instances (no API needed)"""
    
    print("\n" + "="*50)
    print("🐦 SCRAPING TWITTER VIA NITTER...")
    print("="*50)
    
    problems = []
    
    # Nitter instances (some may be down, we try multiple)
    nitter_instances = [
        "https://nitter.net",
        "https://nitter.cz",
        "https://nitter.poast.org",
    ]
    
    # Search queries for problems
    search_terms = [
        "frustrated with app",
        "this app is terrible",
        "looking for alternative",
        "wish there was",
        "Nigeria fintech problem",
        "POS agent scam",
        "bank app down",
        "opay problem",
        "palmpay issue",
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
    }
    
    working_instance = None
    
    # Find a working Nitter instance
    for instance in nitter_instances:
        try:
            response = requests.get(instance, headers=headers, timeout=5)
            if response.status_code == 200:
                working_instance = instance
                print(f"   ✅ Using: {instance}")
                break
        except:
            continue
    
    if not working_instance:
        print("   ⚠️ No Nitter instance available")
        return problems
    
    for term in search_terms:
        try:
            search_url = f"{working_instance}/search?f=tweets&q={term.replace(' ', '+')}"
            
            response = requests.get(search_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find tweet containers
                tweets = soup.find_all('div', class_='timeline-item')
                
                for tweet in tweets[:10]:
                    try:
                        content_div = tweet.find('div', class_='tweet-content')
                        if content_div:
                            content = content_div.get_text(strip=True)
                            
                            # Get tweet link
                            link = tweet.find('a', class_='tweet-link')
                            tweet_url = f"{working_instance}{link['href']}" if link else ""
                            
                            # Get stats
                            stats = tweet.find_all('span', class_='tweet-stat')
                            likes = 0
                            for stat in stats:
                                if 'like' in str(stat).lower():
                                    try:
                                        likes = int(stat.get_text(strip=True).replace(',', ''))
                                    except:
                                        pass
                            
                            if len(content) > 20:
                                problems.append({
                                    "source": "Twitter",
                                    "subsource": term[:20],
                                    "title": content[:100],
                                    "content": content[:400],
                                    "score": likes,
                                    "url": tweet_url.replace(working_instance, "https://twitter.com"),
                                    "unique_id": f"tw_{hash(content) % 10000000}",
                                })
                    except:
                        continue
                        
            time.sleep(1)
            
        except Exception as e:
            print(f"   ⚠️ Search error: {e}")
            continue
    
    print(f"\n   ✅ Twitter Total: {len(problems)}")
    return problems

