# scraper/sources/trends.py

import requests
from bs4 import BeautifulSoup
import time

def scrape_google_trends():
    """Get trending searches from Google Trends"""
    
    print("\n" + "="*50)
    print("📈 SCRAPING GOOGLE TRENDS...")
    print("="*50)
    
    trends = []
    
    try:
        from pytrends.request import TrendReq
        
        pytrends = TrendReq(hl='en-US', tz=360)
        
        # Get trending searches for Nigeria
        trending_ng = pytrends.trending_searches(pn='nigeria')
        
        for idx, row in trending_ng.iterrows():
            trends.append({
                "source": "GoogleTrends",
                "subsource": "Nigeria",
                "title": row[0],
                "content": f"Trending in Nigeria: {row[0]}",
                "score": 100 - idx,  # Higher rank = higher score
                "url": f"https://trends.google.com/trends/explore?q={row[0].replace(' ', '+')}",
                "unique_id": f"gt_ng_{idx}",
            })
        
        # Get global trends
        trending_global = pytrends.trending_searches(pn='united_states')
        
        for idx, row in trending_global.head(20).iterrows():
            trends.append({
                "source": "GoogleTrends",
                "subsource": "Global",
                "title": row[0],
                "content": f"Trending globally: {row[0]}",
                "score": 100 - idx,
                "url": f"https://trends.google.com/trends/explore?q={row[0].replace(' ', '+')}",
                "unique_id": f"gt_us_{idx}",
            })
            
        print(f"   ✅ Trends found: {len(trends)}")
        
    except Exception as e:
        print(f"   ⚠️ pytrends error: {e}")
    
    return trends


def scrape_exploding_topics():
    """Scrape Exploding Topics (free tier)"""
    
    print("\n   🚀 SCRAPING EXPLODING TOPICS...")
    
    trends = []
    
    # ExplodingTopics doesn't have API, we scrape the main page
    url = "https://explodingtopics.com/"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find topic cards (structure may change)
            topic_elements = soup.find_all('div', class_='topic-card')
            
            if not topic_elements:
                # Alternative selectors
                topic_elements = soup.find_all('a', href=True)
                topic_elements = [t for t in topic_elements if '/topic/' in t.get('href', '')]
            
            for i, elem in enumerate(topic_elements[:30]):
                try:
                    title = elem.get_text(strip=True)[:100]
                    href = elem.get('href', '')
                    
                    if title and len(title) > 3:
                        trends.append({
                            "source": "ExplodingTopics",
                            "subsource": "trending",
                            "title": title,
                            "content": f"Exploding topic: {title}",
                            "score": 100 - i,
                            "url": f"https://explodingtopics.com{href}" if href.startswith('/') else href,
                            "unique_id": f"et_{i}_{hash(title) % 10000}",
                        })
                except:
                    continue
                    
            print(f"   ✅ Exploding Topics: {len(trends)}")
            
    except Exception as e:
        print(f"   ⚠️ Exploding Topics error: {e}")
    
    return trends


def scrape_all_trends():
    """Combine all trend sources"""
    
    all_trends = []
    all_trends.extend(scrape_google_trends())
    all_trends.extend(scrape_exploding_topics())
    
    return all_trends