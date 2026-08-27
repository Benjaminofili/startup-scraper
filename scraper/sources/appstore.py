# scraper/sources/appstore.py

import requests
import time
import hashlib

# (country, app_id) - app_id is Apple's numeric ID, found in the App Store
# URL: https://apps.apple.com/<country>/app/<name>/id<APP_ID>
NIGERIAN_IOS_APPS = [
    ("ng", "1463776084"),   # OPay - Beyond Banking (verified)
    ("ng", "1479656820"),   # PalmPay - Transfers, Bills (verified)
    ("ng", "1471941007"),   # Kuda - UNVERIFIED, check before running
    ("ng", "1568647760"),   # PiggyVest - UNVERIFIED, check before running
    ("ng", "675033630"),    # Bolt - UNVERIFIED, check before running
    ("ng", "685890711"),    # Jumia - UNVERIFIED, check before running
]

GLOBAL_IOS_APPS = [
    ("us", "1232780281"),   # Notion
    ("us", "572688855"),    # Todoist
]


def _fetch_reviews_page(country: str, app_id: str, page: int = 1, retries: int = 2):
    """Fetch one page (up to 50 reviews) from Apple's public RSS reviews feed."""
    url = (
        f"https://itunes.apple.com/{country}/rss/customerreviews/"
        f"page={page}/id={app_id}/sortby=mostrecent/json"
    )
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
    }

    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json()
            time.sleep(1)
        except Exception:
            time.sleep(1)
            continue

    return None


def scrape_appstore_reviews(apps=None, pages_per_app=2):
    """Scrape 1-star and 2-star reviews from the Apple App Store"""

    print("\n" + "=" * 50)
    print("🍎 SCRAPING APPLE APP STORE...")
    print("=" * 50)

    if apps is None:
        apps = NIGERIAN_IOS_APPS + GLOBAL_IOS_APPS

    problems = []

    for country, app_id in apps:
        app_problems = 0
        try:
            for page in range(1, pages_per_app + 1):
                data = _fetch_reviews_page(country, app_id, page)

                if not data:
                    break

                entries = data.get("feed", {}).get("entry", [])
                if not entries:
                    break

                # The first "entry" is sometimes the app metadata itself,
                # not a review - skip anything missing a rating/content.
                for entry in entries:
                    rating_label = entry.get("im:rating", {}).get("label")
                    content_label = entry.get("content", {}).get("label", "")

                    if not rating_label or not content_label:
                        continue

                    rating = int(rating_label)
                    if rating > 2 or len(content_label) <= 25:
                        continue

                    review_id = entry.get("id", {}).get("label", "")
                    unique_key = review_id or hashlib.md5(
                        content_label[:50].encode()
                    ).hexdigest()[:16]

                    problems.append({
                        "source": "AppStore",
                        "subsource": f"ios_{app_id}",
                        "title": content_label[:100].replace('\n', ' '),
                        "content": content_label[:600],
                        "score": 0,
                        "rating": rating,
                        "url": f"https://apps.apple.com/{country}/app/id{app_id}",
                        "unique_id": f"as_{unique_key}",
                        "app_id": app_id,
                    })
                    app_problems += 1

                time.sleep(1)  # be nice to Apple's endpoint

            print(f"   📌 App {app_id} ({country}): {app_problems} low-rated reviews")
            time.sleep(1)

        except Exception as e:
            print(f"   ❌ {app_id}: {type(e).__name__}: {e}")
            continue

    print(f"\n   ✅ App Store Total: {len(problems)}")
    return problems