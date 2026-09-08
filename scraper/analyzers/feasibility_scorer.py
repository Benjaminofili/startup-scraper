# scraper/analyzers/feasibility_scorer.py

import re
from typing import Dict, List, Optional, Tuple


# The AI prompt asks for each idea as a block of numbered fields 1..10,
# where field 1 is the idea name and field 10 is "FEASIBILITY SCORES".
# Because the field list itself is numbered (1., 2., ... 10.), the old
# "split on any '<n>. **'" approach shattered every idea into ~10 fake
# "ideas" titled PROBLEM / SOLUTION / FEASIBILITY SCORES, which is why
# every historical feasible_ideas.md just repeats "## 1. FEASIBILITY
# SCORES". We now anchor on the one-per-idea scores block instead.

_SCORE_MARKER = re.compile(r'(?im)^\s*#{0,4}\s*[*_]{0,2}\s*(?:\d+[.)]\s*)?[*_]{0,2}\s*FEASIBILITY\s+SCORES\b')

# Field labels that are NOT idea names - used to reject them when we walk
# backwards from a scores block looking for the idea's title.
_FIELD_LABELS = {
    'idea name', 'problem', 'solution', 'who pays', 'price',
    'existing competitors', 'monetization fit', 'first week', 'why now',
    'feasibility scores', 'feasibility score', 'scores',
}

# A heading / bolded line that could carry an idea name, e.g.
#   "1. **SchoolFeePay**"   "### 2. Mechanic Finder"   "**FarmLink**"
_TITLE_LINE = re.compile(
    r'(?m)^\s*#{0,4}\s*[*_]{0,2}\s*(?:(?:idea\s*)?\d+[.):]\s*)?[*_]{0,2}\s*'
    r'(?:\[)?([A-Za-z0-9][^\n*_\]]{1,60}?)(?:\])?[*_]{0,2}\s*(?:\(.*)?$'
)

_SCORE_PATTERNS = {
    'investment_score': r'Investment(?:\s+Score)?[:\-]?\s*(\d+)\s*(?:/\s*10)?',
    'passive_income_score': r'Passive\s+Income(?:\s+Score)?[:\-]?\s*(\d+)\s*(?:/\s*10)?',
    'team_size_score': r'Team(?:\s+Size)?(?:\s+Score)?[:\-]?\s*(\d+)\s*(?:/\s*10)?',
    'time_to_market_score': r'Time\s+to\s+Market(?:\s+Score)?[:\-]?\s*(\d+)\s*(?:/\s*10)?',
    'competition_score': r'Competition(?:\s+Score)?[:\-]?\s*(\d+)\s*(?:/\s*10)?',
    'monetization_fit_score': r'Monetization\s+Fit(?:\s+Score)?[:\-]?\s*(\d+)\s*(?:/\s*10)?',
    'regulatory_risk_score': r'Regulatory\s+Risk(?:\s+Score)?[:\-]?\s*(\d+)\s*(?:/\s*10)?',
}


def _clean_title(raw: str) -> str:
    """Strip markdown/list cruft and any trailing parenthetical from a title."""
    t = raw.strip().strip('*_#[] ').strip()
    # Drop a leading "N. " / "N) " / "Idea N: " that slipped through.
    t = re.sub(r'^(?:idea\s*)?\d+\s*[.):\-]\s*', '', t, flags=re.IGNORECASE).strip()
    # Drop a trailing parenthetical description.
    t = re.sub(r'\s*\(.*$', '', t).strip()
    return t


def _find_title_before(text: str, end: int, start: int = 0) -> str:
    """
    Walk backwards from `end` over the lines in text[start:end] (the region
    between the previous idea's scores block and this one) and return the
    nearest line that reads like an idea name: a heading or bolded line
    that isn't one of the known numbered field labels. Field lines (2..9 in
    the prompt) and long prose lines are skipped, so the idea's own name -
    usually field 1, many lines up - is what we land on.
    """
    lines = text[start:end].splitlines()
    for line in reversed(lines):
        stripped = line.strip()
        if not stripped:
            continue
        m = _TITLE_LINE.match(line)
        if not m:
            continue
        candidate = _clean_title(m.group(1))
        if not candidate or len(candidate) < 2:
            continue
        if candidate.lower() in _FIELD_LABELS:
            continue
        # Skip lines that are clearly prose rather than a name.
        if len(candidate.split()) > 8:
            continue
        return candidate
    return ''


def parse_feasibility_metrics(ai_analysis: str) -> List[Dict]:
    """
    Parse per-idea feasibility metrics out of the AI analysis.

    Anchors on each "FEASIBILITY SCORES" block (one per idea), reads the
    seven 0-10 scores that follow it, and attaches the idea name found on
    the nearest preceding heading/bold line.
    """
    ideas: List[Dict] = []

    if not ai_analysis:
        return ideas

    markers = list(_SCORE_MARKER.finditer(ai_analysis))
    if not markers:
        return ideas

    for i, marker in enumerate(markers):
        # The scores for this idea run from the marker to the next marker
        # (or end of text). Confine score parsing to this window so one
        # idea's numbers can't bleed into another's.
        scores_start = marker.end()
        scores_end = markers[i + 1].start() if i + 1 < len(markers) else len(ai_analysis)
        scores_text = ai_analysis[scores_start:scores_end]

        search_start = markers[i - 1].end() if i > 0 else 0
        title = _find_title_before(ai_analysis, marker.start(), search_start)

        idea = {
            'raw_text': ai_analysis[marker.start():scores_end].strip(),
            'title': title or f'Idea {i + 1}',
            'investment_score': 5,
            'passive_income_score': 5,
            'team_size_score': 5,
            'time_to_market_score': 5,
            'competition_score': 5,
            'monetization_fit_score': 5,
            'regulatory_risk_score': 5,
            'feasibility_score': 5.0,
        }

        for key, pattern in _SCORE_PATTERNS.items():
            match = re.search(pattern, scores_text, re.IGNORECASE)
            if match:
                idea[key] = min(10, max(0, int(match.group(1))))

        idea['feasibility_score'] = calculate_feasibility_score(
            idea['investment_score'],
            idea['passive_income_score'],
            idea['team_size_score'],
            idea['time_to_market_score'],
            idea['competition_score'],
            idea['monetization_fit_score'],
            idea['regulatory_risk_score'],
        )

        ideas.append(idea)

    return ideas


def calculate_feasibility_score(
    investment: int,
    passive_income: int,
    team_size: int,
    time_to_market: int,
    competition: int = 5,
    monetization_fit: int = 5,
    regulatory_risk: int = 5,
    weights: Optional[Dict[str, float]] = None
) -> float:
    """
    Calculate weighted feasibility score.

    "Cheap and fast to build" (investment/team_size/time_to_market) is no
    longer the majority of the score — it's roughly matched by market-reality
    checks (competition, monetization fit, regulatory risk), because a ₦0
    idea nobody can monetize in a saturated, risky market isn't actually
    feasible just because it's cheap.

    Args:
        investment: Score 0-10 (10 = zero cost)
        passive_income: Score 0-10 (10 = fully automated)
        team_size: Score 0-10 (10 = solo-friendly)
        time_to_market: Score 0-10 (10 = launch in days)
        competition: Score 0-10 (10 = no meaningful existing competitor)
        monetization_fit: Score 0-10 (10 = audience reliably pays for this)
        regulatory_risk: Score 0-10 (10 = no legal/safety/licensing exposure)
        weights: Optional custom weights for each criterion

    Returns:
        Weighted average score (0-100), gated down hard for regulatory risk
    """
    if weights is None:
        weights = {
            'investment': 0.15,
            'passive_income': 0.15,
            'team_size': 0.10,
            'time_to_market': 0.10,
            'competition': 0.20,
            'monetization_fit': 0.20,
            'regulatory_risk': 0.10,
        }

    score = (
        investment * weights['investment'] +
        passive_income * weights['passive_income'] +
        team_size * weights['team_size'] +
        time_to_market * weights['time_to_market'] +
        competition * weights['competition'] +
        monetization_fit * weights['monetization_fit'] +
        regulatory_risk * weights['regulatory_risk']
    ) * 10  # Scale to 0-100

    # Hard gate: severe legal/safety/licensing exposure (e.g. transportation,
    # money transmission, healthcare) shouldn't be masked by a good score on
    # cheap-and-fast dimensions. Cap the ceiling instead of just weighting it.
    if regulatory_risk <= 3:
        score = min(score, 40.0)

    # Hard gate: near-zero monetization fit (audience structurally won't pay,
    # e.g. self-hosting open-source crowd) caps the ceiling too, since this
    # was the exact NoteHub-style trap in the original report.
    if monetization_fit <= 2:
        score = min(score, 45.0)

    return round(score, 1)


def rank_ideas_by_feasibility(ideas: List[Dict]) -> List[Dict]:
    """
    Sort ideas by feasibility score (highest first)
    """
    return sorted(ideas, key=lambda x: x['feasibility_score'], reverse=True)


def get_feasibility_rating(score: float) -> Tuple[str, str]:
    """
    Get human-readable rating and emoji for a feasibility score
    
    Returns:
        (rating, emoji) tuple
    """
    if score >= 80:
        return ("Excellent", "🟢")
    elif score >= 65:
        return ("Good", "🟡")
    elif score >= 50:
        return ("Moderate", "🟠")
    else:
        return ("Low", "🔴")


def format_feasibility_report(ideas: List[Dict], top_n: int = 5) -> str:
    """
    Generate a formatted feasibility report
    """
    if not ideas:
        return "No ideas to analyze."
    
    ranked_ideas = rank_ideas_by_feasibility(ideas)[:top_n]
    
    report = "# 🎯 FEASIBILITY ANALYSIS\n\n"
    report += f"**Total Ideas Analyzed:** {len(ideas)}\n"
    report += f"**Showing Top {len(ranked_ideas)} Most Feasible**\n\n"
    report += "---\n\n"
    
    for i, idea in enumerate(ranked_ideas, 1):
        rating, emoji = get_feasibility_rating(idea['feasibility_score'])
        
        report += f"## {i}. {idea['title']}\n\n"
        report += f"**Overall Feasibility: {idea['feasibility_score']}/100** {emoji} *{rating}*\n\n"
        report += "### Scores Breakdown\n\n"
        report += f"- 💰 **Investment Required:** {idea['investment_score']}/10\n"
        report += f"- 💵 **Passive Income Potential:** {idea['passive_income_score']}/10\n"
        report += f"- 👥 **Team Size (Solo-Friendly):** {idea['team_size_score']}/10\n"
        report += f"- ⚡ **Time to Market:** {idea['time_to_market_score']}/10\n"
        report += f"- 🥊 **Competition (10=blue ocean):** {idea.get('competition_score', 5)}/10\n"
        report += f"- 💳 **Monetization Fit:** {idea.get('monetization_fit_score', 5)}/10\n"
        report += f"- ⚖️ **Regulatory/Legal Risk (10=none):** {idea.get('regulatory_risk_score', 5)}/10\n\n"
        report += "---\n\n"
    
    return report