# scraper/analyzers/ai_analyzer.py

import os
import sys
import traceback

# Groq retires models on a rolling basis and a decommissioned model ID just
# returns an API error - which is exactly how this pipeline went dark:
# llama-3.3-70b-versatile was shut down by Groq on 2026-08-16 and every run
# since then failed the API call, got swallowed below, and produced
# ai_analysis: null with only a generic "did not run" warning.
#
# Default to Groq's recommended replacement, but let a GROQ_MODEL secret
# override it so the *next* retirement is a one-line settings change in the
# repo instead of a code push. Current Groq production model IDs:
#   openai/gpt-oss-120b   (recommended successor to llama-3.3-70b-versatile)
#   openai/gpt-oss-20b
#   llama-3.1-8b-instant
DEFAULT_MODEL = "openai/gpt-oss-120b"


def _gha_annotation(level, message, title=None):
    """
    Emit a GitHub Actions annotation so a failed AI step shows up as a red
    error/warning on the run summary, not just a plain log line nobody
    scrolls to. No-op when not running in Actions.
    """
    if not os.getenv("GITHUB_ACTIONS"):
        return
    # Newlines must be escaped or Actions truncates the annotation at the
    # first line break.
    safe = str(message).replace("\r", "").replace("\n", "%0A")
    prefix = f"::{level} title={title}::" if title else f"::{level}::"
    print(prefix + safe)


def analyze_with_groq(problems, max_items=80):
    """Analyze problems using Groq (free & fast)"""

    # `or` not a getenv default: in CI an unset repo secret is injected as
    # an empty string, not absent, so getenv(..., DEFAULT) would hand back "".
    model = os.getenv("GROQ_MODEL", "").strip() or DEFAULT_MODEL

    print("\n" + "=" * 50)
    print("🤖 AI ANALYSIS WITH GROQ...")
    print(f"   model: {model}")
    print("=" * 50)

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        print("   ⚠️ No GROQ_API_KEY found!")
        print("   Get free key at: https://console.groq.com")
        _gha_annotation("warning", "AI analysis skipped: GROQ_API_KEY is not set",
                        title="Groq")
        return None

    if len(problems) < 5:
        print(f"   ⚠️ Only {len(problems)} items - need more data")
        _gha_annotation("warning",
                        f"AI analysis skipped: only {len(problems)} items to analyze (need >= 5)",
                        title="Groq")
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

        # gpt-oss models spend completion tokens on an internal reasoning
        # pass before the visible answer, so give more headroom than the
        # old llama-3.3 budget or the 5-idea report gets truncated
        # mid-way (which then breaks feasibility parsing downstream).
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=4000
        )

        analysis = response.choices[0].message.content

        if not analysis or not analysis.strip():
            print("   ❌ Groq returned an empty completion")
            _gha_annotation("error",
                            f"Groq model '{model}' returned an empty completion",
                            title="Groq")
            return None

        usage = getattr(response, "usage", None)
        if usage is not None:
            print(f"   📊 tokens: prompt={getattr(usage, 'prompt_tokens', '?')} "
                  f"completion={getattr(usage, 'completion_tokens', '?')}")
        print("   ✅ AI analysis complete!")

        return analysis

    except ImportError as e:
        print(f"   ❌ groq package not installed: {e}")
        _gha_annotation("error", f"AI analysis failed: groq package not importable ({e})",
                        title="Groq")
        return None
    except Exception as e:
        # Surface the ACTUAL cause. The old code printed one line and
        # returned None, so a decommissioned-model error looked identical
        # to a rate limit or a network blip in the log.
        status = getattr(e, "status_code", None) or getattr(e, "code", None)
        body = getattr(e, "body", None) or getattr(e, "message", None)
        detail = f"{type(e).__name__}: {e}"
        if status:
            detail += f" (status={status})"
        if body and str(body) not in str(e):
            detail += f" body={body}"

        print(f"   ❌ Groq call failed with model '{model}': {detail}")
        print("   ----- full traceback -----")
        traceback.print_exc(file=sys.stdout)
        print("   --------------------------")
        _gha_annotation("error",
                        f"AI analysis failed for model '{model}': {detail}. "
                        f"If the model was decommissioned, set the GROQ_MODEL secret "
                        f"to a current one from https://console.groq.com/docs/models",
                        title="Groq")
        return None