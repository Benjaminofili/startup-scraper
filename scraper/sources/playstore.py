# scraper/sources/playstore.py

from google_play_scraper import reviews, Sort, search
import time
import hashlib

# Nigerian apps to analyze
NIGERIAN_APPS = [
    # Fintech (biggest opportunity)
    "com.opay.merchant",
    "com.palmpay.app",
    "team.monipoint.pos",
    "com.kuda.bank",
    "com.cowrywise.android",
    "com.piggyvest.piggyvest",
    "com.carbon.android",
    "com.loanandfund.fairmoney",
    
    # Logistics/Transport
    "com.bolt.ng",
    "com.ubercab",
    "ng.max.app",
    
    # E-commerce
    "com.jumia.android",
    "com.konga.buyer",
    
    # Betting (huge market in Nigeria)
    "com.sportybet.android.ng",
    "com.bet9ja.android",
    
    # Utilities
    "com.buypower.app",
    "ng.gov.firs.tax",
]

# Global apps with common problems
GLOBAL_APPS = [
    "com.notion.id",
    "com.todoist",
    "com.squareup.pos",
]


def scrape_playstore_reviews(apps=None, country='ng', reviews_per_app=60):
    """Scrape 1-star and 2-star reviews from Play Store"""
    
    print("\n" + "=" * 50)
    print("📱 SCRAPING GOOGLE PLAY STORE...")
    print("=" * 50)
    
    if apps is None:
        apps = NIGERIAN_APPS + GLOBAL_APPS
    
    problems = []
    
    for app_id in apps:
        try:
            # Get 1-star reviews (most frustrated users)
            result_1star, _ = reviews(
                app_id,
                lang='en',
                country=country,
                sort=Sort.NEWEST,
                count=reviews_per_app,
                filter_score_with=1
            )
            
            # Also get 2-star reviews (detailed complaints)
            result_2star, _ = reviews(
                app_id,
                lang='en',
                country=country,
                sort=Sort.NEWEST,
                count=reviews_per_app // 2,
                filter_score_with=2
            )
            
            all_reviews = result_1star + result_2star
            app_name = app_id.split('.')[-1].title()
            
            print(f"   📌 {app_name}: {len(all_reviews)} reviews")
            
            for review in all_reviews:
                content = review.get('content', '')
                
                if len(content) > 25:
                    review_id = review.get('reviewId', '')
                    unique_id = review_id or hashlib.md5(content.encode()).hexdigest()[:16]
                    
                    problems.append({
                        "source": "PlayStore",
                        "subsource": app_name,
                        "title": content[:100].replace('\n', ' '),
                        "content": content[:600],
                        "score": review.get('thumbsUpCount', 0),
                        "rating": review.get('score', 1),
                        "url": f"https://play.google.com/store/apps/details?id={app_id}",
                        "unique_id": f"ps_{unique_id}",
                        "app_id": app_id,
                        "date": str(review.get('at', ''))[:10],
                    })
            
            time.sleep(1.5)  # Be nice to Google
            
        except Exception as e:
            print(f"   ❌ {app_id}: {type(e).__name__}: {e}")
            continue
    
    print(f"\n   ✅ Play Store Total: {len(problems)}")
    return problems