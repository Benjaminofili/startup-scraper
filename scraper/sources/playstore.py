# scraper/sources/playstore.py

from google_play_scraper import reviews, Sort, search
import time
import hashlib
from scraper.utils import health

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

# Human-readable names for package ids (package id stays as a separate field).
APP_NAMES = {
    "com.opay.merchant": "OPay", "com.palmpay.app": "PalmPay",
    "team.monipoint.pos": "Moniepoint POS", "com.kuda.bank": "Kuda",
    "com.cowrywise.android": "Cowrywise", "com.piggyvest.piggyvest": "PiggyVest",
    "com.carbon.android": "Carbon", "com.loanandfund.fairmoney": "FairMoney",
    "com.bolt.ng": "Bolt", "com.ubercab": "Uber", "ng.max.app": "MAX",
    "com.jumia.android": "Jumia", "com.konga.buyer": "Konga",
    "com.sportybet.android.ng": "SportyBet", "com.bet9ja.android": "Bet9ja",
    "com.buypower.app": "BuyPower", "ng.gov.firs.tax": "FIRS Tax",
    "com.notion.id": "Notion", "com.todoist": "Todoist",
    "com.squareup.pos": "Square POS",
}

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
    
    attempts = errors = 0
    empty_apps = []
    for app_id in apps:
        try:
            attempts += 1
            n_before = len(problems)
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
            app_name = APP_NAMES.get(app_id, app_id.split('.')[-1].title())
            
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
                        "app_name": app_name,
                        "package_id": app_id,
                        "market": "GooglePlay",
                        "country": country,
                        "date": str(review.get('at', ''))[:10],
                    })
            
            if len(problems) == n_before:
                empty_apps.append(app_id)
            time.sleep(1.5)  # Be nice to Google
            
        except Exception as e:
            print(f"   ❌ {app_id}: {type(e).__name__}: {e}")
            errors += 1
            continue
    
    health.record('playstore', len(problems), attempts, errors, empty_results=len(empty_apps), error=
(f"{len(empty_apps)}/{attempts} apps returned nothing: {', '.join(empty_apps)}" if empty_apps else None))
    print(f"\n   ✅ Play Store Total: {len(problems)}")
    return problems