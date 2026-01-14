# scraper/sources/github_issues.py

import requests
import time

def scrape_github_issues():
    """Scrape GitHub issues for feature requests and problems"""
    
    print("\n" + "="*50)
    print("🐙 SCRAPING GITHUB ISSUES...")
    print("="*50)
    
    problems = []
    
    # Popular repos where people request features
    repos = [
        # Productivity tools
        "notion-enhancer/notion-enhancer",
        "toeverything/AFFiNE",
        "AppFlowy-IO/AppFlowy",
        
        # Developer tools  
        "vercel/next.js",
        "supabase/supabase",
        
        # Finance
        "maybe-finance/maybe",
        "actualbudget/actual",
        
        # African tech
        "PaystackHQ/paystack-android",
    ]
    
    # Search queries for issues
    search_queries = [
        "is:issue is:open label:enhancement",
        "is:issue is:open label:feature-request", 
        "is:issue is:open label:help-wanted",
        "is:issue is:open \"would be nice\"",
        "is:issue is:open \"feature request\"",
    ]
    
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "StartupScraper/1.0"
    }
    
    # Check GITHUB_TOKEN for higher rate limits
    github_token = os.environ.get('GITHUB_TOKEN')
    if github_token:
        headers["Authorization"] = f"token {github_token}"
        print("   🔑 Using GitHub token for higher limits")
    
    # Method 1: Search specific repos
    for repo in repos:
        try:
            url = f"https://api.github.com/repos/{repo}/issues"
            params = {"state": "open", "per_page": 30, "sort": "reactions"}
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                issues = response.json()
                
                for issue in issues:
                    # Skip pull requests
                    if 'pull_request' in issue:
                        continue
                    
                    title = issue.get('title', '')
                    body = issue.get('body', '') or ''
                    
                    # Look for feature requests and problems
                    labels = [l.get('name', '').lower() for l in issue.get('labels', [])]
                    
                    is_feature = any(l in ['enhancement', 'feature', 'feature-request', 'help wanted'] 
                                    for l in labels)
                    
                    if is_feature or issue.get('reactions', {}).get('total_count', 0) > 5:
                        problems.append({
                            "source": "GitHub",
                            "subsource": repo.split('/')[1],
                            "title": title[:150],
                            "content": f"{title}\n\n{body}"[:600],
                            "score": issue.get('reactions', {}).get('total_count', 0),
                            "comments": issue.get('comments', 0),
                            "url": issue.get('html_url', ''),
                            "unique_id": f"gh_{issue.get('id', '')}",
                            "labels": labels,
                        })
                
                print(f"   📌 {repo}: {len(issues)} issues")
                
            time.sleep(0.5)
            
        except Exception as e:
            print(f"   ❌ {repo}: {e}")
            continue
    
    # Method 2: Global search for trending feature requests
    search_url = "https://api.github.com/search/issues"
    
    trending_queries = [
        "is:issue is:open reactions:>10 \"feature request\"",
        "is:issue is:open reactions:>5 \"would love\"",
        "is:issue is:open reactions:>5 \"please add\"",
    ]
    
    for query in trending_queries:
        try:
            params = {"q": query, "sort": "reactions", "per_page": 20}
            response = requests.get(search_url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                items = response.json().get('items', [])
                
                for issue in items:
                    problems.append({
                        "source": "GitHub",
                        "subsource": "trending",
                        "title": issue.get('title', '')[:150],
                        "content": issue.get('body', '')[:600] if issue.get('body') else '',
                        "score": issue.get('reactions', {}).get('total_count', 0),
                        "url": issue.get('html_url', ''),
                        "unique_id": f"ghs_{issue.get('id', '')}",
                    })
                    
            time.sleep(1)
            
        except Exception:
            continue
    
    print(f"\n   ✅ GitHub Total: {len(problems)}")
    return problems


# Need to import os at top
import os