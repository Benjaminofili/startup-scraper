# scraper/analyzers/ai_analyzer.py

import os


def analyze_with_groq(problems, max_items=80):
    """Analyze problems using Groq (free & fast)"""
    
    print("\n" + "=" * 50)
    print("🤖 AI ANALYSIS WITH GROQ...")
    print("=" * 50)
    
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        print("   ⚠️ No GROQ_API_KEY found!")
        print("   Get free key at: https://console.groq.com")
        return None
    
    if len(problems) < 5:
        print(f"   ⚠️ Only {len(problems)} items - need more data")
        return None
    
    try:
        from groq import Groq
        
        client = Groq(api_key=api_key)
        
        # Group by source
        by_source = {}
        for p in problems[:max_items]:
            src = p.get('source', 'Unknown')
            if src not in by_source:
                by_source[src] = []
            by_source[src].append(p)
        
        # Format for AI
        formatted = ""
        for source, items in by_source.items():
            formatted += f"\n\n=== {source} ({len(items)} items) ===\n"
            for item in items[:15]:
                formatted += f"- {item['title'][:80]}"
                if item.get('content'):
                    formatted += f": {item['content'][:80]}"
                formatted += "\n"
        
        prompt = f"""You are a startup advisor for Nigerian university students.

TEAM:
- 3 developers (Android, web, APIs)
- 1 marketer (social media)
- Resources: Play Store account, AWS free tier
- Budget: ₦0 (zero)
- Location: Nigeria

PROBLEMS FROM REAL USERS:
{formatted}

Find TOP 5 STARTUP OPPORTUNITIES.

For each:

1. **PROBLEM** (1 sentence)
2. **SOLUTION** (simple app/service)
3. **WHO PAYS** (specific customer)
4. **PRICE** (in ₦ Naira)
5. **FIRST WEEK** (3 concrete steps)
6. **WHY NOW** (based on complaints)

Be specific. Nigerian market first. No capital required."""

        print(f"   📤 Analyzing {len(problems)} problems...")
        
        response = client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=3000
        )
        
        analysis = response.choices[0].message.content
        print("   ✅ AI analysis complete!")
        
        return analysis
        
    except ImportError:
        print("   ❌ groq package not installed")
        return None
    except Exception as e:
        print(f"   ❌ Groq error: {type(e).__name__}: {e}")
        return None