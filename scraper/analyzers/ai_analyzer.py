# scraper/analyzers/ai_analyzer.py

import os
from groq import Groq

def analyze_with_groq(problems, max_items=100):
    """Analyze problems using Groq (free, fast)"""
    
    print("\n" + "="*50)
    print("🤖 AI ANALYSIS WITH GROQ...")
    print("="*50)
    
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        print("   ⚠️ No GROQ_API_KEY found!")
        print("   Get free key at: https://console.groq.com")
        return None
    
    if len(problems) < 5:
        print(f"   ⚠️ Only {len(problems)} items - need more data")
        return None
    
    try:
        client = Groq(api_key=api_key)
        
        # Group problems by source for better context
        by_source = {}
        for p in problems[:max_items]:
            src = p.get('source', 'Unknown')
            if src not in by_source:
                by_source[src] = []
            by_source[src].append(p)
        
        # Format problems for AI
        formatted = ""
        for source, items in by_source.items():
            formatted += f"\n\n=== {source} ({len(items)} items) ===\n"
            for item in items[:20]:  # Max 20 per source
                formatted += f"- {item['title'][:80]}"
                if item.get('content'):
                    formatted += f": {item['content'][:100]}"
                formatted += "\n"
        
        prompt = f"""You are a startup advisor helping Nigerian university students find business opportunities.

TEAM PROFILE:
- 3 developers (can build Android apps, web apps, APIs)
- 1 marketer (handles social media, growth)
- Resources: Play Store account, AWS free tier
- Budget: ₦0 (zero naira for ads/hosting initially)
- Location: Nigeria

SCRAPED PROBLEMS FROM REAL USERS:
{formatted}

YOUR TASK:
Analyze these complaints and identify the TOP 7 STARTUP OPPORTUNITIES.

For each opportunity, provide:

1. **PROBLEM STATEMENT** (1-2 sentences)
   What specific pain are people experiencing?

2. **PROPOSED SOLUTION** 
   What app/service would solve this?

3. **TARGET CUSTOMER**
   Who exactly would pay? Be specific.

4. **REVENUE MODEL**
   How will you make money? Include ₦ pricing.

5. **COMPETITION CHECK**
   What existing solutions are failing?

6. **FIRST WEEK ACTIONS**
   3 concrete steps to validate this idea.

7. **WHY THIS WILL WORK**
   Based on the complaints, why is now the right time?

IMPORTANT:
- Prioritize ideas that can be built in 2-4 weeks
- Focus on Nigerian market first (you understand it)
- No ideas requiring heavy capital or licenses
- Prefer recurring revenue over one-time payments

Be specific and practical."""

        print(f"   📤 Sending {len(problems)} problems to Groq...")
        
        response = client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=4000
        )
        
        analysis = response.choices[0].message.content
        print("   ✅ AI analysis complete!")
        
        return analysis
        
    except Exception as e:
        print(f"   ❌ Groq error: {type(e).__name__}: {e}")
        return None


def analyze_with_gemini(problems, max_items=100):
    """Backup: Analyze using Google Gemini (also free)"""
    
    print("\n   🔄 Trying Gemini as backup...")
    
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("   ⚠️ No GEMINI_API_KEY found")
        return None
    
    try:
        import google.generativeai as genai
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        
        # Format problems
        formatted = "\n".join([
            f"- [{p['source']}] {p['title'][:60]}: {p.get('content', '')[:80]}"
            for p in problems[:max_items]
        ])
        
        prompt = f"""Analyze these user complaints and find 5 startup ideas for Nigerian students with no budget:

{formatted}

For each idea: Problem, Solution, Who Pays, Price in ₦, First Step."""

        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        print(f"   ❌ Gemini error: {e}")
        return None