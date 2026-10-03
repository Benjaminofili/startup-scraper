# scraper/analyzers/ai_analyzer.py

import json
import os
import sys
import traceback

# Groq retires models on a rolling basis and a decommissioned model ID just
# returns an API error - which is exactly how this pipeline went dark:
# llama-3.3-70b-versatile was shut down by Groq on 2026-08-16 and every run
# since then failed the API call, got swallowed, and produced
# ai_analysis: null with only a generic "did not run" warning.
#
# Default to Groq's recommended replacement, but let a GROQ_MODEL secret
# override it so the *next* retirement is a settings change, not a code push.
# Structured outputs (strict JSON schema) are used, so the override must be
# a model that supports them (openai/gpt-oss-120b / -20b do).
DEFAULT_MODEL = "openai/gpt-oss-120b"

SCORE_KEYS = ["investment", "passive_income", "team_size", "time_to_market",
              "competition", "monetization_fit", "regulatory_risk"]

_STR_LIST = {"type": "array", "items": {"type": "string"}}

SCHEMA = {
    "type": "object",
    "properties": {
        "ideas": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "observed_problem": {"type": "string"},
                    "evidence_ids": _STR_LIST,
                    "affected_user_hypothesis": {"type": "string"},
                    "solution_hypothesis": {"type": "string"},
                    "monetization_hypothesis": {"type": "string"},
                    "alternatives_to_verify": _STR_LIST,
                    "unknowns": _STR_LIST,
                    "validation_steps": _STR_LIST,
                    "scores": {
                        "type": "object",
                        "properties": {k: {"type": "integer"} for k in SCORE_KEYS},
                        "required": SCORE_KEYS,
                        "additionalProperties": False,
                    },
                },
                "required": ["name", "observed_problem", "evidence_ids",
                             "affected_user_hypothesis", "solution_hypothesis",
                             "monetization_hypothesis", "alternatives_to_verify",
                             "unknowns", "validation_steps", "scores"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["ideas"],
    "additionalProperties": False,
}

PROMPT = """You are a skeptical startup due-diligence analyst. You are given
scraped user complaints and discussions. Separate what the data OBSERVES
from what you are GUESSING. Never state a market size, price point,
competitor list or willingness-to-pay as established fact: the data does
not contain them. Anything not supported by the items below is a
hypothesis or an unknown that needs external validation.

TEAM CONTEXT (constraints only, not evidence):
- 3 developers (Android, web, APIs), 1 marketer
- Play Store account, AWS free tier, budget: zero
- Location: Nigeria

SCRAPED ITEMS (each prefixed with its [evidence id]):
{formatted}

Return exactly 5 opportunities. For each:
- name: short product name
- observed_problem: one sentence, only what the cited items actually say
- evidence_ids: ids copied from the items above that support it (at least 2 if possible)
- affected_user_hypothesis: who plausibly has this problem (a hypothesis)
- solution_hypothesis: a simple app/service idea
- monetization_hypothesis: how it might earn money (a hypothesis; no invented prices stated as fact)
- alternatives_to_verify: existing alternatives you believe exist and that must be checked
- unknowns: what the data does not tell us
- validation_steps: 3 concrete steps to test it cheaply
- scores: integers 0-10 for investment (10 = zero cost), passive_income (10 = fully
  automated), team_size (10 = solo-friendly), time_to_market (10 = days),
  competition (10 = no meaningful competitor, 0 = strong incumbents),
  monetization_fit (10 = audience reliably pays, 0 = expects free),
  regulatory_risk (10 = no licensing or legal exposure, 0 = licenses, safety or
  money transmission). Be conservative.
Keep every text field to 1-2 short sentences."""


def _gha_annotation(level, message, title=None):
    """
    Emit a GitHub Actions annotation so a failed AI step shows up as a red
    error/warning on the run summary. No-op when not running in Actions.
    """
    if not os.getenv("GITHUB_ACTIONS"):
        return
    safe = str(message).replace("\r", "").replace("\n", "%0A")
    prefix = f"::{level} title={title}::" if title else f"::{level}::"
    print(prefix + safe)


def analyze_with_groq(problems, max_items=80):
    """
    Analyze problems using Groq strict structured outputs.

    Returns {"ideas": [...], "meta": {...}} or None on failure. The model is
    constrained to a JSON schema, so there is no Markdown/regex parsing
    downstream and no format drift between models.
    """

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

        # Group by source; include ids so the model can cite evidence.
        by_source = {}
        for p in problems[:max_items]:
            by_source.setdefault(p.get('source', 'Unknown'), []).append(p)

        formatted = ""
        valid_ids = set()
        ai_input = 0
        for source, items in by_source.items():
            formatted += f"\n\n=== {source} ({min(len(items), 15)} items) ===\n"
            for item in items[:15]:
                uid = item.get('unique_id', '')
                valid_ids.add(uid)
                ai_input += 1
                formatted += f"- [{uid}] {item['title'][:80]}"
                if item.get('content'):
                    formatted += f": {item['content'][:80]}"
                formatted += "\n"

        prompt = PROMPT.format(formatted=formatted)
        print(f"   📤 Analyzing {ai_input} items ({len(problems)} candidates)...")

        # gpt-oss spends completion tokens on reasoning before the answer;
        # retry once with a bigger budget if the first pass is cut off.
        data = None
        finish_reason = None
        usage = None
        for budget in (8000, 16000):
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=budget,
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": "startup_opportunities",
                                    "strict": True, "schema": SCHEMA},
                },
            )
            choice = response.choices[0]
            finish_reason = getattr(choice, "finish_reason", None)
            usage = getattr(response, "usage", None)
            print(f"   📊 finish_reason={finish_reason} max_tokens={budget} "
                  f"completion_tokens={getattr(usage, 'completion_tokens', '?')}")
            if finish_reason == "length":
                print("   ⚠️ completion truncated; "
                      + ("retrying with a larger budget" if budget == 8000 else "giving up"))
                continue
            content = choice.message.content
            if not content or not content.strip():
                break
            data = json.loads(content)
            break

        if not data or not data.get("ideas"):
            why = ("truncated (finish_reason=length) at max budget"
                   if finish_reason == "length" else "empty or invalid completion")
            print(f"   ❌ Groq returned no usable analysis: {why}")
            _gha_annotation("error",
                            f"Groq model '{model}' returned no usable analysis: {why}",
                            title="Groq")
            return None

        # Keep only evidence ids that really exist in the prompt.
        for idea in data["ideas"]:
            idea["evidence_ids"] = [e for e in idea.get("evidence_ids", []) if e in valid_ids]

        print(f"   ✅ AI analysis complete: {len(data['ideas'])} ideas")
        return {
            "ideas": data["ideas"],
            "meta": {
                "model": model,
                "finish_reason": finish_reason,
                "ai_input": ai_input,
                "completion_tokens": getattr(usage, "completion_tokens", None),
            },
        }

    except ImportError as e:
        print(f"   ❌ groq package not installed: {e}")
        _gha_annotation("error", f"AI analysis failed: groq package not importable ({e})",
                        title="Groq")
        return None
    except Exception as e:
        # Surface the ACTUAL cause (type, status, body, traceback) and an
        # Actions annotation; never swallow it into a bare None.
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
