# scraper/sources/trends.py

import requests
from bs4 import BeautifulSoup
import time


def scrape_google_trends():
    """Get trending searches from Google Trends"""
    
    print("\n" + "=" * 50)
    print("📈 SCRAPING GOOGLE TRENDS...")
    print("=" * 50)
    
    trends = []
    
    try:
        from pytrends.request import TrendReq
        
        pytrends = TrendReq(hl='en-US', tz=360)
        
        # Nigeria trends
        try:
            trending_ng = pytrends.trending_searches(pn='nigeria')
            
            for idx, row in trending_ng.head(20).iterrows():
                trends.append({
                    "source": "GoogleTrends",
                    "subsource": "Nigeria",
                    "title": str(row[0]),
                    "content": f"Trending in Nigeria: {row[0]}",
                    "score": 100 - idx,
                    "url": f"https://trends.google.com/trends/explore?q={str(row[0]).replace(' ', '+')}",
                    "unique_id": f"gt_ng_{idx}",
                })
            
            print(f"   ✅ Nigeria trends: {len(trending_ng)}")
            
        except Exception as e:
            print(f"   ⚠️ Nigeria trends failed: {e}")
        
        # US/Global trends
        try:
            trending_us = pytrends.trending_searches(pn='united_states')
            
            for idx, row in trending_us.head(15).iterrows():
                trends.append({
                    "source": "GoogleTrends",
                    "subsource": "Global",
                    "title": str(row[0]),
                    "content": f"Trending globally: {row[0]}",
                    "score": 80 - idx,
                    "url": f"https://trends.google.com/trends/explore?q={str(row[0]).replace(' ', '+')}",
                    "unique_id": f"gt_us_{idx}",
                })
                
            print(f"   ✅ Global trends: {len(trending_us)}")
            
        except Exception as e:
            print(f"   ⚠️ Global trends failed: {e}")
        
    except ImportError:
        print("   ⚠️ pytrends not installed")
    except Exception as e:
        print(f"   ⚠️ Google Trends error: {e}")
    
    return trends


def scrape_all_trends():
    """Combine all trend sources"""
    
    all_trends = []
    all_trends.extend(scrape_google_trends())
    
    print(f"\n   ✅ Trends Total: {len(all_trends)}")
    return all_trends