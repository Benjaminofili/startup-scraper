# scraper/sources/nairaland.py

import requests
from bs4 import BeautifulSoup
import time
import random

def scrape_nairaland():
    """Scrape Nairaland with better anti-blocking"""
    
    print("\n" + "="*50)
    print("🇳🇬 SCRAPING NAIRALAND...")
    print("="*50)
    
    problems = []
    
    # Rotate user agents
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    ]
    
    sections = [
        ("business", "Business"),
        ("investment", "Investment"),
        ("jobs", "Jobs"),
        ("technology-market", "Tech"),
        ("phones", "Phones"),
        ("autos", "Cars"),
        ("properties", "Property"),
        ("travel", "Travel"),
        ("education", "Education"),
    ]
    
    problem_keywords = [
        'help', 'how', 'need', 'problem', 'issue', 'advice',
        'pls', 'please', 'urgent', 'scam', 'wahala', 'abeg',
        'recommend', 'which', 'best', 'looking', 'where', 'fake',
        'frustrated', 'bad', 'terrible', 'avoid', 'warning'
    ]
    
    for section_url, section_name in sections:
        for page in range(4):  # More pages
            try:
                url = f"https://www.nairaland.com/{section_url}/{page}"
                
                headers = {
                    "User-Agent": random.choice(user_agents),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                    "Referer": "https://www.nairaland.com/",
                }
                
                response = requests.get(url, headers=headers, timeout=15)
                
                if response.status_code == 403:
                    print(f"   🚫 Blocked on {section_name}")
                    break
                
                if response.status_code != 200:
                    continue
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Multiple selectors for topics
                topics = []
                
                # Method 1: Featured and bold topics
                for td in soup.find_all('td', class_=['featured', 'bold']):
                    link = td.find('a')
                    if link:
                        topics.append(link)
                
                # Method 2: Topic table rows
                for tr in soup.find_all('tr'):
                    link = tr.find('a')
                    if link and '/topic/' in str(link.get('href', '')):
                        topics.append(link)
                
                page_count = 0
                for link in topics:
                    title = link.get_text(strip=True)
                    href = link.get('href', '')
                    
                    if len(title) > 10 and any(kw in title.lower() for kw in problem_keywords):
                        full_url = href if href.startswith('http') else f"https://www.nairaland.com{href}"
                        
                        problems.append({
                            "source": "Nairaland",
                            "subsource": section_name,
                            "title": title[:150],
                            "content": title,
                            "score": 0,
                            "url": full_url,
                            "unique_id": f"nl_{hash(href) % 10000000}",
                        })
                        page_count += 1
                
                if page_count > 0:
                    print(f"   📌 {section_name} p{page}: {page_count} topics")
                
                # Random delay to avoid blocking
                time.sleep(random.uniform(1.0, 2.0))
                
            except Exception as e:
                print(f"   ❌ {section_name}: {type(e).__name__}")
                continue
    
    print(f"\n   ✅ Nairaland Total: {len(problems)}")
    return problems