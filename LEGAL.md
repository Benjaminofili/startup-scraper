# Legal & Ethical Scraping Guidelines

## ✅ Allowed Sources (Low Risk)

### Google Play Store
- **Status:** Public data
- **Rate Limit:** 1-2 requests per second
- **Data:** Only public reviews (no personal data)

### Hacker News
- **Status:** Official free API
- **Documentation:** https://github.com/HackerNews/API
- **Rate Limit:** No official limit, be respectful (1 req/sec)

### GitHub
- **Status:** Official API with free tier
- **Documentation:** https://docs.github.com/en/rest
- **Rate Limit:** 60 req/hour (unauthenticated), 5000/hour (with token)

### Reddit (via PullPush)
- **Status:** Third-party archive of public data
- **Note:** Not affiliated with Reddit
- **Risk:** Medium - Reddit changed API in 2023

### Nairaland
- **Status:** No robots.txt restrictions
- **Rate Limit:** Be very slow (2+ seconds between requests)
- **Risk:** May block IPs, no legal risk for public posts


## ⚠️ Caution Sources (Medium Risk)

### Google Trends (pytrends)
- **Status:** Unofficial library
- **Risk:** May break anytime, Google doesn't officially support

### Exploding Topics
- **Status:** Scraping their website
- **Risk:** They could block you, check their ToS


## ❌ Avoided Sources (High Risk)

### Twitter/X
- **Status:** Explicitly prohibits scraping
- **ToS:** https://twitter.com/en/tos (Section 4)
- **Legal History:** Sued hiQ Labs, threatened others
- **Alternative:** Apply for Twitter API v2

### LinkedIn
- **Status:** Very aggressive anti-scraping
- **Legal History:** Multiple lawsuits (hiQ vs LinkedIn)
- **NEVER scrape LinkedIn**

### Facebook
- **Status:** Scraping prohibited
- **Alternative:** Facebook Graph API (requires approval)


## Best Practices

1. **Rate Limiting:** Always add delays between requests
2. **User-Agent:** Use a real browser user-agent
3. **robots.txt:** Check and respect it
4. **Personal Data:** Never collect emails, phone numbers, etc.
5. **Caching:** Don't re-scrape the same content repeatedly
6. **Attribution:** Link back to original sources


## Data Retention

- Keep scraped data for maximum 30 days
- Don't redistribute raw scraped data
- Only use for analysis and idea generation


## Disclaimer

This tool is for educational and personal research purposes.
Users are responsible for ensuring their use complies with
applicable laws and terms of service of scraped websites.