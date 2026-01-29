# scraper/main.py

import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import sources
from scraper.sources.playstore import scrape_playstore_reviews
from scraper.sources.reddit import scrape_reddit_all
from scraper.sources.hackernews import scrape_hackernews
from scraper.sources.github_issues import scrape_github_issues
from scraper.sources.nairaland import scrape_nairaland
from scraper.sources.trends import scrape_all_trends

# Import utilities
from scraper.utils.deduplicator import deduplicate_problems
from scraper.utils.storage import save_results

# Import analyzers
from scraper.analyzers.ai_analyzer import analyze_with_groq
from scraper.analyzers.keyword_extractor import extract_keywords, categorize_problems
from scraper.analyzers.feasibility_scorer import (
    parse_feasibility_metrics,
    rank_ideas_by_feasibility,
    format_feasibility_report
)


def main():
    """Main scraper orchestrator"""
    
    print("\n" + "=" * 70)
    print(f"🚀 STARTUP PROBLEM SCRAPER")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    
    all_problems = []
    source_stats = {}
    
    # ============================================
    # 1. RUN ALL SCRAPERS
    # ============================================
    
    scrapers = [
        ("PlayStore", scrape_playstore_reviews),
        ("HackerNews", scrape_hackernews),
        ("GitHub", scrape_github_issues),
        ("Nairaland", scrape_nairaland),
        ("Trends", scrape_all_trends),
        ("Reddit", scrape_reddit_all),
    ]
    
    for name, scraper_func in scrapers:
        try:
            results = scraper_func()
            all_problems.extend(results)
            source_stats[name] = len(results)
        except Exception as e:
            print(f"   ❌ {name} failed: {type(e).__name__}: {e}")
            source_stats[name] = 0
    
    # ============================================
    # 2. DEDUPLICATE
    # ============================================
    
    print("\n" + "=" * 50)
    print("🔄 DEDUPLICATION...")
    print("=" * 50)
    
    print(f"   Raw: {len(all_problems)}")
    unique_problems = deduplicate_problems(all_problems)
    print(f"   Unique: {len(unique_problems)}")
    
    # Sort by score
    unique_problems.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    # ============================================
    # 3. LOCAL ANALYSIS
    # ============================================
    
    print("\n" + "=" * 50)
    print("📊 KEYWORD ANALYSIS...")
    print("=" * 50)
    
    keywords = extract_keywords(unique_problems, top_n=15)
    print("\n   Top Keywords:")
    for word, count in keywords[:10]:
        print(f"      {word}: {count}")
    
    categories = categorize_problems(unique_problems)
    print("\n   Categories:")
    for cat, items in sorted(categories.items(), key=lambda x: -len(x[1]))[:5]:
        print(f"      {cat}: {len(items)}")
    
    # ============================================
    # 4. AI ANALYSIS
    # ============================================
    
    ai_analysis = analyze_with_groq(unique_problems)
    
    # ============================================
    # 5. FEASIBILITY ANALYSIS
    # ============================================
    
    feasibility_ideas = []
    feasibility_report = None
    
    if ai_analysis:
        print("\n" + "=" * 50)
        print("🎯 FEASIBILITY ANALYSIS...")
        print("=" * 50)
        
        feasibility_ideas = parse_feasibility_metrics(ai_analysis)
        
        if feasibility_ideas:
            ranked_ideas = rank_ideas_by_feasibility(feasibility_ideas)
            feasibility_report = format_feasibility_report(ranked_ideas, top_n=5)
            
            print(f"\n   📊 Analyzed {len(feasibility_ideas)} ideas")
            print("\n   Top 3 Most Feasible:")
            for i, idea in enumerate(ranked_ideas[:3], 1):
                print(f"      {i}. {idea['title']} - Score: {idea['feasibility_score']}/100")
        else:
            print("   ⚠️ Could not parse feasibility metrics from AI output")
    
    # ============================================
    # 6. SAVE RESULTS
    # ============================================
    
    print("\n" + "=" * 50)
    print("💾 SAVING...")
    print("=" * 50)
    
    metadata = {
        "sources": source_stats,
        "top_keywords": keywords[:15],
        "feasibility_ideas": feasibility_ideas
    }
    
    saved = save_results(
        problems=unique_problems[:150],
        ai_analysis=ai_analysis,
        feasibility_report=feasibility_report,
        metadata=metadata
    )
    
    for name, path in saved.items():
        print(f"   📁 {name}: {path}")
    
    # ============================================
    # 7. SUMMARY
    # ============================================
    
    print("\n" + "=" * 70)
    print("✅ COMPLETE!")
    print("=" * 70)
    
    print(f"\n   📊 Total: {len(unique_problems)} problems")
    print("\n   By Source:")
    for src, count in sorted(source_stats.items(), key=lambda x: -x[1]):
        status = "✅" if count > 0 else "❌"
        print(f"      {status} {src}: {count}")
    
    if ai_analysis:
        print("\n   💡 Check data/latest_ideas.md for opportunities!")
    
    if feasibility_report:
        print("   🎯 Check data/feasible_ideas.md for top feasible ideas!")
    
    return unique_problems


if __name__ == "__main__":
    main()