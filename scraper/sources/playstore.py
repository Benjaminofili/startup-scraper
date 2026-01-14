# scraper/sources/playstore.py

from google_play_scraper import reviews, Sort, search
import time
import hashlib

# Nigerian fintech apps
NIGERIAN_APPS = [
    # Fintech
    "com.opay.merchant",
    "com.palmpay.app",
    "team.monipoint.pos",
    "com.kuda.bank",
    "com.cowrywise.android",
    "com.piggyvest.piggyvest",
    "com.carbon.android",
    "com.loanandfund.fairmoney",
    "ng.gov.firs.tax",
    
    # Logistics
    "com.glotrack.app",
    "com.gokada.android",
    "com.bolt.ng",
    "com.max.maxng",
    
    # E-commerce
    "com.jumia.android",
    "com.konga.buyer",
    
    # Betting (huge market)
    "com.sportybet.android.ng",
    "com.bet9ja.android",
]

# Global popular apps with problems
GLOBAL_APPS = [
    # Productivity
    "com.notion.id",
    "com.todoist",
    "com.ticktick.task",
    
    # Finance
    "com.robinhood.android",
    "com.coinbase.android",
    
    # SMB Tools
    "com.squareup.pos",
    "com.intuit.quickbooks",
]


def scrape_playstore_reviews(apps=None, country='ng', reviews_per_app=80):
    """Scrape 1-star and 2-star reviews from Play Store"""
    
    print("\n" + "="*50)
    print("📱 SCRAPING GOOGLE PLAY STORE...")
    print("="*50)
    
    if apps is None:
        apps = NIGERIAN_APPS + GLOBAL_APPS
    
    problems = []
    
    for app_id in apps:
        try:
            # Get 1-star reviews
            result_1star, _ = reviews(
                app_id,
                lang='en',
                country=country,
                sort=Sort.NEWEST,
                count=reviews_per_app,
                filter_score_with=1
            )
            
            # Get 2-star reviews too (often more detailed)
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
            
            time.sleep(1.2)
            
        except Exception as e:
            print(f"   ❌ {app_id}: {type(e).__name__}")
            continue
    
    print(f"\n   ✅ Play Store Total: {len(problems)}")
    return problems


def find_bad_apps_in_category(category, country='ng'):
    """Find apps with high downloads but low ratings (opportunity!)"""
    
    print(f"\n   🔍 Searching bad apps in: {category}")
    
    opportunities = []
    
    try:
        results = search(
            category,
            lang='en',
            country=country,
            n_hits=30
        )
        
        for app in results:
            # High downloads (>100k) but bad rating (<3.5)
            installs = app.get('installs', '0').replace(',', '').replace('+', '')
            try:
                install_count = int(installs)
            except:
                install_count = 0
                
            rating = app.get('score', 5)
            
            if install_count > 100000 and rating and rating < 3.5:
                opportunities.append({
                    "app_id": app.get('appId'),
                    "title": app.get('title'),
                    "rating": rating,
                    "installs": app.get('installs'),
                    "opportunity": "High demand, poor execution"
                })
                
    except Exception as e:
        print(f"   ❌ Category search error: {e}")
    
    return opportunities