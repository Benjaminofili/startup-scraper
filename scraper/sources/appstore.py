# scraper/sources/appstore.py

from app_store_scraper import AppStore
import time
import hashlib

# app_name is the URL slug, app_id is Apple's numeric ID - both required
# by app-store-scraper. Find via: https://apps.apple.com/<country>/app/<name>/id<APP_ID>
NIGERIAN_IOS_APPS = [
    # (country, app_name, app_id)
    ("ng", "opay-fast-mobile-payment", "1067169791"),
    ("ng", "palmpay", "1440384008"),
    ("ng", "kuda-money-app", "1471941007"),
    ("ng", "piggyvest", "1568647760"),
    ("ng", "bolt-request-a-ride", "675033630"),
    ("ng", "jumia-online-shopping", "685890711"),
]

GLOBAL_IOS_APPS = [
    ("us", "notion-notes-docs-tasks", "1232780281"),
    ("us", "todoist-to-do-list-planner", "572688855"),
]


def scrape_appstore_reviews(apps=None, reviews_per_app=60):
    """Scrape 1-star and 2-star reviews from the Apple App Store"""

    print("\n" + "=" * 50)
    print("🍎 SCRAPING APPLE APP STORE...")
    print("=" * 50)

    if apps is None:
        apps = NIGERIAN_IOS_APPS + GLOBAL_IOS_APPS

    problems = []

    for country, app_name, app_id in apps:
        try:
            app = AppStore(country=country, app_name=app_name, app_id=app_id)
            app.review(how_many=reviews_per_app)

            display_name = app_name.replace('-', ' ').title()
            print(f"   📌 {display_name}: {len(app.reviews)} reviews fetched")

            for review in app.reviews:
                content = review.get('review', '') or ''
                rating = review.get('rating', 5)

                if len(content) > 25 and rating <= 2:
                    unique_key = f"{app_id}_{review.get('date', '')}_{content[:30]}"
                    unique_id = hashlib.md5(unique_key.encode()).hexdigest()[:16]

                    problems.append({
                        "source": "AppStore",
                        "subsource": display_name,
                        "title": content[:100].replace('\n', ' '),
                        "content": content[:600],
                        "score": 0,  # Apple doesn't expose a helpful-vote count via this lib
                        "rating": rating,
                        "url": f"https://apps.apple.com/{country}/app/{app_name}/id{app_id}",
                        "unique_id": f"as_{unique_id}",
                        "app_id": app_id,
                        "date": str(review.get('date', ''))[:10],
                    })

            time.sleep(1.5)  # Be nice to Apple's endpoint

        except Exception as e:
            print(f"   ❌ {app_name}: {type(e).__name__}: {e}")
            continue

    print(f"\n   ✅ App Store Total: {len(problems)}")
    return problems
