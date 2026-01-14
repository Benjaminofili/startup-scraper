# scraper/sources/github_issues.py

import requests
import time
import os


def scrape_github_issues():
    """Scrape GitHub issues for feature requests"""
    
    print("\n" + "=" * 50)
    print("🐙 SCRAPING GITHUB ISSUES...")
    print("=" * 50)
    
    problems = []
    
    # Popular repos where people request features
    repos = [
        "toeverything/AFFiNE",
        "AppFlowy-IO/AppFlowy",
        "actualbudget/actual",
        "maybe-finance/maybe",
        "calcom/cal.com",
        "twentyhq/twenty",
    ]
    
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "StartupScraper/1.0"
    }
    
    # Use token if available for higher rate limits
    github_token = os.environ.get('GITHUB_TOKEN')
    if github_token:
        headers["Authorization"] = f"token {github_token}"
        print("   🔑 Using GitHub token")
    
    for repo in repos:
        try:
            url = f"https://api.github.com/repos/{repo}/issues"
            params = {"state": "open", "per_page": 25, "sort": "reactions"}
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                issues = response.json()
                
                repo_name = repo.split('/')[1]
                
                for issue in issues:
                    # Skip pull requests
                    if 'pull_request' in issue:
                        continue
                    
                    title = issue.get('title', '')
                    body = issue.get('body', '') or ''
                    
                    labels = [l.get('name', '').lower() for l in issue.get('labels', [])]
                    
                    # Look for feature requests
                    is_feature = any(l in ['enhancement', 'feature', 'feature-request', 'help wanted']
                                     for l in labels)
                    
                    reactions = issue.get('reactions', {}).get('total_count', 0)
                    
                    if is_feature or reactions > 3:
                        problems.append({
                            "source": "GitHub",
                            "subsource": repo_name,
                            "title": title[:150],
                            "content": f"{title}\n\n{body}"[:600],
                            "score": reactions,
                            "comments": issue.get('comments', 0),
                            "url": issue.get('html_url', ''),
                            "unique_id": f"gh_{issue.get('id', '')}",
                            "labels": labels,
                        })
                
                print(f"   📌 {repo_name}: {len(issues)} issues")
                
            time.sleep(0.5)
            
        except Exception as e:
            print(f"   ❌ {repo}: {e}")
            continue
    
    print(f"\n   ✅ GitHub Total: {len(problems)}")
    return problems