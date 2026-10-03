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
from scraper.utils.normalize import add_signal, stratified_sample
from scraper.utils import health
from collections import Counter

# Import analyzers
from scraper.analyzers.ai_analyzer import analyze_with_groq
from scraper.analyzers.keyword_extractor import extract_keywords, categorize_problems
from scraper.analyzers.feasibility_scorer import (
    ideas_from_structured,
    format_ideas_markdown,
    rank_ideas_by_feasibility,
    format_feasibility_report
)


def main():
    """Main scraper orchestrator"""
    
    print("\n" + "=" * 70)
    print(f"🚀 STARTUP PROBLEM SCRAPER")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    
    health.reset()
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
    # Per-source percentile signal; raw `score` isn't comparable across sources.
    add_signal(all_problems)
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

    insufficient_new = len(new_problems) < 5
    if insufficient_new:
        # Do NOT fall back to the stale unique set: re-feeding old evidence
        # to the AI is what recreated variations of the same old ideas.
        print("   ⚠️ insufficient_new_evidence: fewer than 5 unseen items.")
        print("      Skipping AI idea generation this run (data still saved).")
        if os.getenv("GITHUB_ACTIONS"):
            print("::warning title=Scraper::insufficient_new_evidence - AI analysis skipped, fewer than 5 unseen items")
        analysis_input = new_problems
    else:
        # Stratified across sources by normalized signal - not "highest raw
        # score wins", which let HN points crowd out Play/App Store reviews.
        analysis_input = stratified_sample(new_problems, len(new_problems))

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
    
    ai_result = None if insufficient_new else analyze_with_groq(analysis_input)
    ai_analysis = None  # markdown rendering of validated ideas
    
    # ============================================
    # 5. FEASIBILITY ANALYSIS
    # ============================================
    
    feasibility_ideas = []
    feasibility_report = None
    
    if ai_result:
        print("\n" + "=" * 50)
        print("🎯 FEASIBILITY ANALYSIS...")
        print("=" * 50)
        
        feasibility_ideas = ideas_from_structured(ai_result)
        if feasibility_ideas:
            ai_analysis = format_ideas_markdown(feasibility_ideas)
        
        if feasibility_ideas:
            # Only evidence-verified (PASS) ideas get ranked; WEAK ones are
            # shown in latest_ideas.md flagged, FAIL ones live in metadata.
            ranked_ideas = rank_ideas_by_feasibility(
                [i for i in feasibility_ideas if i.get('evidence_status') == 'PASS']
            ) or rank_ideas_by_feasibility(feasibility_ideas)
            feasibility_report = format_feasibility_report(ranked_ideas, top_n=5)
            
            print(f"\n   📊 Analyzed {len(feasibility_ideas)} ideas")
            print("\n   Top 3 Most Feasible:")
            for i, idea in enumerate(ranked_ideas[:3], 1):
                print(f"      {i}. {idea['title']} - Score: {idea['feasibility_score']}/100")
        else:
            print("   ⚠️ AI returned ideas but none passed score validation")
    
    # ============================================
    # 6. SAVE RESULTS
    # ============================================
    
    print("\n" + "=" * 50)
    print("💾 SAVING...")
    print("=" * 50)
    
    stored_sample = stratified_sample(unique_problems, 150)
    ai_meta = (ai_result or {}).get("meta", {})

    metadata = {
        "sources": source_stats,
        "source_health": health.snapshot(),
        # raw/unique/new are pipeline-stage counts; analysis_candidates is
        # what was eligible for the AI, ai_input is what actually entered
        # the prompt (capped per source), stored is the saved sample.
        "counts": {
            "raw": len(all_problems),
            "unique": len(unique_problems),
            "new": len(new_problems),
            "analysis_candidates": len(analysis_input),
            "ai_input": ai_meta.get("ai_input", 0),
            "stored": len(stored_sample),
            "run_status": "insufficient_new_evidence" if insufficient_new else "ok",
        },
        "subsource_counts": {
            f"{src}/{sub}": n for (src, sub), n in sorted(
                Counter((p.get("source", "?"), p.get("subsource", "?")) for p in unique_problems).items()
            )
        },
        "ai": ai_meta,
        "rejected_ideas": [
            {"name": r.get("name"), "observed_problem": r.get("observed_problem"),
             "evidence_ids": r.get("evidence_ids"), "evidence_verdicts": r.get("evidence_verdicts")}
            for r in (ai_result or {}).get("rejected", [])
        ],
        "top_keywords": keywords[:15],
        "feasibility_ideas": feasibility_ideas,
    }

    saved = save_results(
        problems=stored_sample,
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
    # Skipping for lack of new evidence is not an AI failure.
    ai_ok = ai_analysis is not None or insufficient_new
    if not ai_ok:
        print("\n" + "!" * 70)
        print("❌ AI ANALYSIS DID NOT PRODUCE OUTPUT - see the Groq error above.")
        print("!" * 70)

    return ai_ok


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)