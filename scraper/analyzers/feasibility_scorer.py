# scraper/analyzers/feasibility_scorer.py

import re
from typing import Dict, List, Optional, Tuple


def parse_feasibility_metrics(ai_analysis: str) -> List[Dict]:
    """
    Parse feasibility metrics from AI-generated analysis
    
    Expected format in AI output:
    - Investment: X/10
    - Passive Income: X/10
    - Team Size: X/10
    - Time to Market: X/10
    """
    ideas = []
    
    if not ai_analysis:
        return ideas
    
    # Split by numbered ideas (1., 2., 3., etc.)
    idea_sections = re.split(r'\n(?=\d+\.\s+\*\*)', ai_analysis)
    
    for section in idea_sections:
        if not section.strip():
            continue
        
        idea = {
            'raw_text': section,
            'title': '',
            'investment_score': 5,
            'passive_income_score': 5,
            'team_size_score': 5,
            'time_to_market_score': 5,
            'feasibility_score': 5.0
        }
        
        # Extract title (first line after number)
        title_match = re.search(r'\d+\.\s+\*\*(.+?)\*\*', section)
        if title_match:
            idea['title'] = title_match.group(1).strip()
        
        # Extract scores (look for patterns like "Investment: 8/10" or "Investment Score: 8")
        patterns = {
            'investment_score': r'Investment(?:\s+Score)?:\s*(\d+)(?:/10)?',
            'passive_income_score': r'Passive\s+Income(?:\s+Score)?:\s*(\d+)(?:/10)?',
            'team_size_score': r'Team(?:\s+Size)?(?:\s+Score)?:\s*(\d+)(?:/10)?',
            'time_to_market_score': r'Time\s+to\s+Market(?:\s+Score)?:\s*(\d+)(?:/10)?'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, section, re.IGNORECASE)
            if match:
                score = int(match.group(1))
                # Normalize to 0-10 if needed
                idea[key] = min(10, max(0, score))
        
        # Calculate overall feasibility score
        idea['feasibility_score'] = calculate_feasibility_score(
            idea['investment_score'],
            idea['passive_income_score'],
            idea['team_size_score'],
            idea['time_to_market_score']
        )
        
        if idea['title']:  # Only add if we found a title
            ideas.append(idea)
    
    return ideas


def calculate_feasibility_score(
    investment: int,
    passive_income: int,
    team_size: int,
    time_to_market: int,
    weights: Optional[Dict[str, float]] = None
) -> float:
    """
    Calculate weighted feasibility score
    
    Args:
        investment: Score 0-10 (10 = zero cost)
        passive_income: Score 0-10 (10 = fully automated)
        team_size: Score 0-10 (10 = solo-friendly)
        time_to_market: Score 0-10 (10 = launch in days)
        weights: Optional custom weights for each criterion
    
    Returns:
        Weighted average score (0-10)
    """
    if weights is None:
        # Default weights - prioritize low investment and passive income
        weights = {
            'investment': 0.35,      # 35% - Most important
            'passive_income': 0.30,  # 30% - Very important
            'team_size': 0.20,       # 20% - Important
            'time_to_market': 0.15   # 15% - Nice to have
        }
    
    score = (
        investment * weights['investment'] +
        passive_income * weights['passive_income'] +
        team_size * weights['team_size'] +
        time_to_market * weights['time_to_market']
    ) * 10  # Scale to 0-100
    
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
        report += f"- ⚡ **Time to Market:** {idea['time_to_market_score']}/10\n\n"
        report += "---\n\n"
    
    return report
