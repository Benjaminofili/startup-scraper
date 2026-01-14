# scraper/main.py

import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import scrapers
from scraper.sources import (
    scrape_playstore_reviews,
    scrape_reddit_all,
    scrape_hackernews,
    scrape_github_issues,
    scrape_nairaland,
    scrape_all_trends,
)

# Import utilities
from scraper.utils.deduplicator import deduplicate_problems, merge_duplicates
from scraper.utils.storage import save_results, cleanup_old_files

# Import analyzers
from scraper.analyzers.ai_analyzer import analyze_with_groq, analyze_with_gemini
from scraper.analyzers.keyword_extractor import (
    extract_keywords,
    categorize_problems,
    rank_problems_by_opportunity,
    generate_keyword_report,
)


def main():
    """Main scraping orchestrator"""
    
    print("\n" + "="*70)
    print(f"🚀 STARTUP PROBLEM SCRAPER")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*70)
    
    all_problems = []
    source_stats = {}
    
    # ============================================
    # 1. RUN SCRAPERS
    # ============================================
    
    scrapers = [
        ("PlayStore", scrape_playstore_reviews),
        ("Reddit", scrape_reddit_all),
        ("HackerNews", scrape_hackernews),
        ("GitHub", scrape_github_issues),
        ("Nairaland", scrape_nairaland),
        ("Trends", scrape_all_trends),
    ]
    
    for name, scraper_func in scrapers:
        try:
            print(f"\n{'='*50}")
            results = scraper_func()
            all_problems.extend(results)
            source_stats[name] = len(results)
            print(f"   ✅ {name}: {len(results)} items")
        except Exception as e:
            print(f"   ❌ {name} failed: {type(e).__name__}: {e}")
            source_stats[name] = 0
    
    # ============================================
    # 2. DEDUPLICATE
    # ============================================
    
    print("\n" + "="*50)
    print("🔄 PROCESSING DATA...")
    print("="*50)
    
    print(f"   Raw items: {len(all_problems)}")
    
    # Deduplicate
    unique_problems = deduplicate_problems(all_problems)
    print(f"   After dedup: {len(unique_problems)}")
    
    # Merge duplicates to find cross-validated problems
    merged_problems = merge_duplicates(all_problems)
    cross_validated = [p for p in merged_problems if p.get('cross_validated')]
    print(f"   Cross-validated: {len(cross_validated)}")
    
    # ============================================
    # 3. LOCAL ANALYSIS (Free, No API)
    # ============================================
    
    print("\n" + "="*50)
    print("📊 LOCAL KEYWORD ANALYSIS...")
    print("="*50)
    
    # Extract keywords
    top_keywords = extract_keywords(unique_problems, top_n=30)
    print("\n   Top Keywords:")
    for word, count in top_keywords[:10]:
        print(f"      {word}: {count}")
    
    # Categorize
    categories = categorize_problems(unique_problems)
    print("\n   Categories:")
    for cat, items in sorted(categories.items(), key=lambda x: -len(x[1]))[:5]:
        print(f"      {cat}: {len(items)}")
    
    # Rank by opportunity
    ranked_problems = rank_problems_by_opportunity(unique_problems)
    
    # Generate keyword report
    keyword_report = generate_keyword_report(unique_problems)
    
    # ============================================
    # 4. AI ANALYSIS (if API key available)
    # ============================================
    
    ai_analysis = None
    
    if os.getenv("GROQ_API_KEY"):
        ai_analysis = analyze_with_groq(ranked_problems[:100])
    
    if not ai_analysis and os.getenv("GEMINI_API_KEY"):
        ai_analysis = analyze_with_gemini(ranked_problems[:100])
    
    if not ai_analysis:
        print("\n   ⚠️ No AI API key found - using local analysis only")
        ai_analysis = keyword_report
    
    # ============================================
    # 5. SAVE RESULTS
    # ============================================
    
    print("\n" + "="*50)
    print("💾 SAVING RESULTS...")
    print("="*50)
    
    metadata = {
        "sources": source_stats,
        "cross_validated_count": len(cross_validated),
        "top_keywords": top_keywords[:20],
        "categories": {k: len(v) for k, v in categories.items()},
    }
    
    saved_files = save_results(
        problems=ranked_problems[:200],
        ai_analysis=ai_analysis,
        metadata=metadata
    )
    
    for file_type, path in saved_files.items():
        print(f"   📁 {file_type}: {path}")
    
    # Cleanup old files (keep last 30 days)
    cleanup_old_files(keep_days=30)
    
    # ============================================
    # 6. SUMMARY
    # ============================================
    
    print("\n" + "="*70)
    print("✅ COMPLETE!")
    print("="*70)
    print(f"\n   📊 Total Problems: {len(unique_problems)}")
    print(f"   🔥 Cross-Validated: {len(cross_validated)}")
    print(f"   💡 Check data/latest_ideas.md for opportunities")
    
    # Show preview of top problems
    print("\n   🎯 TOP 5 OPPORTUNITIES:")
    for i, p in enumerate(ranked_problems[:5], 1):
        score = p.get('opportunity_score', 0)
        print(f"   {i}. [{p['source']}] (score: {score:.0f})")
        print(f"      {p['title'][:70]}...")
    
    return ranked_problems


if __name__ == "__main__":
    main()