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
        
        prompt = f"""You are a skeptical startup due-diligence analyst reviewing ideas for a
Nigerian university team, not a hype generator. Your job is to find ideas that
would survive scrutiny from a professional investor, not just ideas that are
cheap to build.

TEAM:
- 3 developers (Android, web, APIs)
- 1 marketer (social media)
- Resources: Play Store account, AWS free tier
- Budget: ₦0 (zero)
- Location: Nigeria

PROBLEMS FROM REAL USERS:
{formatted}

Find TOP 5 STARTUP OPPORTUNITIES. Favor ideas with real evidence of unmet
demand over ideas that are merely cheap or fast to build — a ₦0-capital idea
in an oversaturated market is worse than a slightly harder idea nobody else
is doing well.

For each idea, provide:

1. **[IDEA NAME]**

2. **PROBLEM** (1 sentence - what pain point this solves, citing the specific
   complaint/source it came from)

3. **SOLUTION** (simple app/service description)

4. **WHO PAYS** (specific customer segment)

5. **PRICE** (in ₦ Naira - monthly/per transaction)

6. **EXISTING COMPETITORS** (name specific real alternatives already serving
   this need, even free/open-source/informal ones. If you cannot think of
   any, say "None identified" rather than assuming a blue ocean.)

7. **MONETIZATION FIT** (1-2 sentences: is this specific audience segment
   actually known to pay for this category of product, or are they typically
   price-sensitive / expect free tools? Be honest even if it hurts the idea.)

8. **FIRST WEEK** (3 concrete steps to launch)

9. **WHY NOW** (based on user complaints above)

10. **FEASIBILITY SCORES** (Rate each 0-10):
    - Investment: X/10 (10 = ₦0 needed, 0 = high capital)
    - Passive Income: X/10 (10 = fully automated, 0 = manual work)
    - Team Size: X/10 (10 = solo-friendly, 0 = large team needed)
    - Time to Market: X/10 (10 = days to launch, 0 = months)
    - Competition: X/10 (10 = no meaningful existing competitor, 0 = many
      strong well-funded competitors already serve this exact need — score
      based on what you named in EXISTING COMPETITORS above, don't just
      default to a high number)
    - Monetization Fit: X/10 (10 = this exact audience segment reliably pays
      for this type of product, 0 = this audience is known to expect free
      tools or self-host / pirate alternatives — base this on MONETIZATION
      FIT above)
    - Regulatory Risk: X/10 (10 = no licensing, safety, or legal liability
      concerns, 0 = requires licenses, involves physical safety, money
      transmission, healthcare, or transportation liability)

Be specific and skeptical. Do not inflate scores to make an idea look better
than the evidence supports. If competitors clearly already dominate a space,
say so plainly even if it makes the idea look weak."""

        print(f"   📤 Analyzing {len(problems)} problems...")
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
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