# scraper/main.py

import os
import requests
from bs4 import BeautifulSoup
from google_play_scraper import reviews, Sort
from groq import Groq
import json
import time
from datetime import datetime

# Get API key from environment (GitHub Secrets)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Nigerian apps to analyze
NIGERIAN_APPS = [
    "com.opay.merchant",
    "com.palmpay.app",
    "team.monipoint.pos",
    "com.kuda.bank",
    "com.cowrywise.android",
]


def scrape_reddit_pullpush():
    """Scrape Reddit using Pullpush (no API key needed)"""
    
    print("\n🔍 SCRAPING REDDIT...")
    
    problems = []
    base_url = "https://api.pullpush.io/reddit/search/submission/"
    
    subreddits = ["entrepreneur", "startups", "smallbusiness", "SaaS", "Nigeria"]
    queries = ["need help", "frustrated", "looking for", "any recommendations"]
    
    for subreddit in subreddits:
        for query in queries:
            try:
                params = {
                    "subreddit": subreddit,
                    "q": query,
                    "size": 25,
                    "sort_type": "score"
                }
                
                response = requests.get(base_url, params=params, timeout=20)
                data = response.json()
                posts = data.get("data", [])
                
                for post in posts:
                    if post.get("score", 0) >= 5:
                        problems.append({
                            "source": f"Reddit r/{subreddit}",
                            "title": post.get("title", ""),
                            "content": post.get("selftext", "")[:300],
                            "score": post.get("score", 0),
                            "url": f"https://reddit.com{post.get('permalink', '')}",
                        })
                
                time.sleep(0.3)
            except Exception as e:
                print(f"   Error: {e}")
                continue
    
    print(f"   ✅ Found {len(problems)} Reddit problems")
    return problems


def scrape_nairaland():
    """Scrape Nairaland for Nigerian problems"""
    
    print("\n🇳🇬 SCRAPING NAIRALAND...")
    
    problems = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    sections = [
        ("business", "Business"),
        ("investment", "Investment"),
        ("jobs", "Jobs"),
        ("technology-market", "Tech"),
    ]
    
    problem_words = ['help', 'how', 'need', 'problem', 'issue', 'advice', 
                     'pls', 'please', 'urgent', 'scam', 'wahala', 'abeg']
    
    for section_url, section_name in sections:
        for page in range(2):
            try:
                url = f"https://www.nairaland.com/{section_url}/{page}"
                response = requests.get(url, headers=headers, timeout=15)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                for td in soup.find_all('td', class_='featured') + soup.find_all('td', class_='bold'):
                    link = td.find('a')
                    if link:
                        title = link.text.strip()
                        href = link.get('href', '')
                        
                        if any(word in title.lower() for word in problem_words):
                            problems.append({
                                "source": f"Nairaland {section_name}",
                                "title": title,
                                "content": "",
                                "score": 0,
                                "url": f"https://www.nairaland.com{href}" if href.startswith('/') else href,
                            })
                
                time.sleep(0.5)
            except Exception as e:
                print(f"   Error: {e}")
                continue
    
    print(f"   ✅ Found {len(problems)} Nairaland problems")
    return problems


def scrape_playstore():
    """Scrape 1-star reviews from Play Store"""
    
    print("\n📱 SCRAPING PLAY STORE...")
    
    problems = []
    
    for app_id in NIGERIAN_APPS:
        try:
            result, _ = reviews(
                app_id,
                lang='en',
                country='ng',
                sort=Sort.NEWEST,
                count=50,
                filter_score_with=1
            )
            
            for review in result:
                content = review.get('content', '')
                if len(content) > 20:
                    problems.append({
                        "source": f"PlayStore {app_id.split('.')[-1]}",
                        "title": "1-Star Review",
                        "content": content[:300],
                        "score": review.get('thumbsUpCount', 0),
                        "url": f"https://play.google.com/store/apps/details?id={app_id}",
                    })
            
            time.sleep(1)
            
        except Exception as e:
            print(f"   Error with {app_id}: {e}")
    
    print(f"   ✅ Found {len(problems)} Play Store problems")
    return problems


def analyze_with_ai(problems):
    """Use Groq to find best opportunities"""
    
    print("\n🤖 ANALYZING WITH AI...")
    
    if not GROQ_API_KEY:
        print("   ⚠️ No Groq API key. Skipping AI analysis.")
        return None
    
    try:
        client = Groq(api_key=GROQ_API_KEY)
        
        problems_text = "\n".join([
            f"- [{p['source']}] {p['title'][:80]}: {p['content'][:100]}"
            for p in problems[:60]
        ])
        
        prompt = f"""You are a startup advisor for Nigerian students.

They have: 3 developers, 1 marketer, Play Store account, NO MONEY.

Analyze these complaints/problems:

{problems_text}

Find TOP 5 STARTUP OPPORTUNITIES:

For each:
1. THE PROBLEM (one sentence)
2. THE SOLUTION (simple app)
3. WHO PAYS (customer)
4. PRICE (in Naira)
5. FIRST STEP (this week)

Be practical for students with no funding."""

        response = client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=2000
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"   ❌ AI error: {e}")
        return None


def main():
    """Main scraping function"""
    
    print("=" * 60)
    print(f"🚀 STARTUP SCRAPER - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    
    all_problems = []
    
    # Run scrapers
    all_problems.extend(scrape_reddit_pullpush())
    all_problems.extend(scrape_nairaland())
    all_problems.extend(scrape_playstore())
    
    # Remove duplicates
    seen = set()
    unique_problems = []
    for p in all_problems:
        if p['title'] not in seen:
            seen.add(p['title'])
            unique_problems.append(p)
    
    # Sort by score
    unique_problems.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    print(f"\n📊 TOTAL PROBLEMS: {len(unique_problems)}")
    
    # AI Analysis
    ai_analysis = analyze_with_ai(unique_problems)
    
    # Create results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    
    results = {
        "timestamp": timestamp,
        "total_problems": len(unique_problems),
        "problems": unique_problems[:100],  # Top 100
        "ai_analysis": ai_analysis
    }
    
    # Save to data folder
    os.makedirs("data", exist_ok=True)
    
    # Save JSON
    with open(f"data/results_{timestamp}.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Save latest (always overwritten)
    with open("data/latest_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Save AI analysis as text
    if ai_analysis:
        with open(f"data/ideas_{timestamp}.txt", "w", encoding="utf-8") as f:
            f.write(f"STARTUP IDEAS - {timestamp}\n")
            f.write("=" * 60 + "\n\n")
            f.write(ai_analysis)
        
        with open("data/latest_ideas.txt", "w", encoding="utf-8") as f:
            f.write(f"STARTUP IDEAS - {timestamp}\n")
            f.write("=" * 60 + "\n\n")
            f.write(ai_analysis)
    
    print("\n✅ DONE!")
    print(f"   Results: data/results_{timestamp}.json")
    print(f"   Ideas: data/ideas_{timestamp}.txt")
    
    return results


if __name__ == "__main__":
    main()