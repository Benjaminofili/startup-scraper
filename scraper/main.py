# scraper/main.py

import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import sources
from scraper.sources.playstore import scrape_playstore_reviews
from scraper.sources.appstore import scrape_appstore_reviews
from scraper.sources.reddit import scrape_reddit_all
from scraper.sources.hackernews import scrape_hackernews
from scraper.sources.github_issues import scrape_github_issues
from scraper.sources.nairaland import scrape_nairaland
from scraper.sources.trends import scrape_all_trends
from scraper.sources.nigerian_tech_blogs import scrape_nigerian_tech_blogs

# Import utilities
from scraper.utils.deduplicator import deduplicate_problems
from scraper.utils.storage import save_results
from scraper.utils.state_tracker import load_seen_ids, save_seen_ids, filter_new

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
        ("AppStore", scrape_appstore_reviews),
        ("HackerNews", scrape_hackernews),
        ("GitHub", scrape_github_issues),
        ("Nairaland", scrape_nairaland),
        ("Trends", scrape_all_trends),
        ("Reddit", scrape_reddit_all),
        ("NigerianTechBlogs", scrape_nigerian_tech_blogs),
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
    print(f"   Unique (this run): {len(unique_problems)}")

    # ============================================
    # 2b. FILTER OUT CONTENT SEEN IN PRIOR RUNS
    # ============================================
    # This is the fix for the "closed feedback loop" problem: without this,
    # every run re-feeds the same recurring HN/Reddit threads into the AI
    # analyzer, which is why weeks of "fresh" ideas turned out to be the
    # same 5 concepts repackaged under different names.

    print("\n" + "=" * 50)
    print("🆕 FILTERING PREVIOUSLY-SEEN CONTENT...")
    print("=" * 50)

    seen_ids = load_seen_ids()
    print(f"   Known from prior runs: {len(seen_ids)} unique_ids")

    new_problems = filter_new(unique_problems, seen_ids)
    print(f"   New this run: {len(new_problems)} / {len(unique_problems)}")

    if len(new_problems) < 5:
        print("   ⚠️ Very little new content this run - sources may need")
        print("      wider rotation pools, or this run just landed on a")
        print("      quiet period. Falling back to full unique set so the")
        print("      AI analysis isn't starved of input.")
        analysis_input = unique_problems
    else:
        analysis_input = new_problems

    # Sort by score
    analysis_input.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    # ============================================
    # 3. LOCAL ANALYSIS
    # ============================================
    
    print("\n" + "=" * 50)
    print("📊 KEYWORD ANALYSIS...")
    print("=" * 50)
    
    keywords = extract_keywords(analysis_input, top_n=15)
    print("\n   Top Keywords:")
    for word, count in keywords[:10]:
        print(f"      {word}: {count}")
    
    categories = categorize_problems(analysis_input)
    print("\n   Categories:")
    for cat, items in sorted(categories.items(), key=lambda x: -len(x[1]))[:5]:
        print(f"      {cat}: {len(items)}")
    
    # ============================================
    # 4. AI ANALYSIS
    # ============================================
    
    ai_analysis = analyze_with_groq(analysis_input)
    
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
    # 6b. UPDATE SEEN-ID TRACKER
    # ============================================
    # Mark everything from this run as seen, so future runs' dedup filter
    # knows about it - this is what makes the rotation/dedup actually
    # compound over time instead of resetting on every run.

    updated_seen_ids = seen_ids | {p.get('unique_id') for p in unique_problems if p.get('unique_id')}
    save_seen_ids(updated_seen_ids)
    print(f"   🧠 Seen-ID tracker: {len(seen_ids)} -> {len(updated_seen_ids)}")

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

    # The scraped data is already saved above, so a green run still needs
    # to fail loudly when the AI stage produced nothing - otherwise the
    # pipeline silently degrades to "just a scraper" for weeks (which is
    # exactly what happened when Groq decommissioned the old model).
    ai_ok = ai_analysis is not None
    if not ai_ok:
        print("\n" + "!" * 70)
        print("❌ AI ANALYSIS DID NOT PRODUCE OUTPUT - see the Groq error above.")
        print("!" * 70)

    return ai_ok


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)