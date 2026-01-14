# scraper/sources/__init__.py

from .playstore import scrape_playstore_reviews
from .reddit import scrape_reddit_all
from .hackernews import scrape_hackernews
from .github_issues import scrape_github_issues
from .nairaland import scrape_nairaland
from .trends import scrape_all_trends

# Twitter removed due to legal concerns - uncomment at your own risk
# from .twitter import scrape_twitter_nitter

__all__ = [
    'scrape_playstore_reviews',
    'scrape_reddit_all', 
    'scrape_hackernews',
    'scrape_github_issues',
    'scrape_nairaland',
    'scrape_all_trends',
]