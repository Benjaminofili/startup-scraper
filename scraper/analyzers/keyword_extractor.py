# scraper/analyzers/keyword_extractor.py

"""
Local keyword extraction without external APIs.
Uses simple NLP techniques - no AI costs!
"""

import re
from collections import Counter
from typing import List, Dict, Tuple


# Common words to ignore
STOP_WORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
    'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 
    'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that',
    'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'my',
    'your', 'his', 'her', 'its', 'our', 'their', 'what', 'which', 'who',
    'when', 'where', 'why', 'how', 'all', 'each', 'every', 'both', 'few',
    'more', 'most', 'other', 'some', 'such', 'no', 'not', 'only', 'own',
    'same', 'so', 'than', 'too', 'very', 'just', 'also', 'now', 'here',
    'there', 'then', 'once', 'if', 'because', 'about', 'into', 'through',
    'during', 'before', 'after', 'above', 'below', 'between', 'under',
    'again', 'further', 'then', 'once', 'any', 'been', 'being', 'get',
    'got', 'getting', 'like', 'really', 'even', 'still', 'app', 'use',
    'using', 'used', 'want', 'need', 'dont', "don't", 'cant', "can't",
    'im', "i'm", 'ive', "i've", 'its', "it's", 'thats', "that's",
}

# Problem indicator words (boost these)
PROBLEM_INDICATORS = {
    'frustrated', 'annoying', 'hate', 'terrible', 'awful', 'worst',
    'broken', 'bug', 'error', 'crash', 'slow', 'expensive', 'waste',
    'scam', 'fake', 'useless', 'difficult', 'confusing', 'complicated',
    'missing', 'lacking', 'wish', 'hope', 'please', 'help', 'need',
    'looking', 'searching', 'alternative', 'replacement', 'better',
    'problem', 'issue', 'trouble', 'struggle', 'fail', 'failed',
    'disappointment', 'disappointed', 'bad', 'poor', 'horrible',
    # Nigerian slang
    'wahala', 'abeg', 'pls', 'urgent', 'wey', 'dey', 'una',
}

# Category keywords
CATEGORY_KEYWORDS = {
    'fintech': ['payment', 'bank', 'money', 'transfer', 'wallet', 'loan', 
                'credit', 'debit', 'account', 'transaction', 'pos', 'atm',
                'opay', 'palmpay', 'kuda', 'moniepoint', 'cowrywise'],
    
    'ecommerce': ['shop', 'buy', 'sell', 'order', 'delivery', 'shipping',
                  'product', 'store', 'cart', 'checkout', 'price', 'jumia',
                  'konga', 'jiji'],
    
    'logistics': ['delivery', 'shipping', 'tracking', 'driver', 'rider',
                  'dispatch', 'courier', 'gig', 'bolt', 'uber', 'max'],
    
    'productivity': ['task', 'schedule', 'calendar', 'reminder', 'note',
                     'document', 'collaborate', 'team', 'project', 'workflow'],
    
    'education': ['learn', 'course', 'student', 'teacher', 'school',
                  'university', 'study', 'exam', 'assignment', 'jamb', 'waec'],
    
    'health': ['doctor', 'hospital', 'medicine', 'health', 'appointment',
               'pharmacy', 'drug', 'prescription', 'symptom', 'diagnosis'],
    
    'entertainment': ['stream', 'movie', 'music', 'game', 'video', 'watch',
                      'play', 'content', 'creator', 'tiktok', 'youtube'],
    
    'real_estate': ['rent', 'house', 'apartment', 'property', 'landlord',
                    'tenant', 'agent', 'accommodation', 'hostel'],
    
    'jobs': ['job', 'work', 'hire', 'salary', 'career', 'remote', 'freelance',
             'interview', 'resume', 'cv', 'employment', 'employer'],
    
    'betting': ['bet', 'odds', 'stake', 'win', 'sportybet', 'bet9ja',
                'betking', 'nairabet', 'football', 'prediction'],
}


def tokenize(text: str) -> List[str]:
    """Split text into tokens (words)"""
    
    if not text:
        return []
    
    # Lowercase
    text = text.lower()
    
    # Remove URLs
    text = re.sub(r'http\S+|www\S+', '', text)
    
    # Remove special characters but keep apostrophes for contractions
    text = re.sub(r"[^a-zA-Z0-9'\s]", ' ', text)
    
    # Split and filter
    tokens = text.split()
    tokens = [t.strip("'") for t in tokens if len(t) > 2]
    
    return tokens


def extract_keywords(
    problems: List[Dict],
    top_n: int = 50,
    min_frequency: int = 2
) -> List[Tuple[str, int]]:
    """
    Extract most common keywords from problems.
    Returns list of (keyword, count) tuples.
    """
    
    all_tokens = []
    
    for problem in problems:
        # Combine title and content
        text = f"{problem.get('title', '')} {problem.get('content', '')}"
        tokens = tokenize(text)
        
        # Filter stop words
        tokens = [t for t in tokens if t not in STOP_WORDS]
        
        all_tokens.extend(tokens)
    
    # Count frequencies
    counter = Counter(all_tokens)
    
    # Boost problem indicator words
    for word in PROBLEM_INDICATORS:
        if word in counter:
            counter[word] *= 2
    
    # Filter by minimum frequency
    filtered = [(word, count) for word, count in counter.items() 
                if count >= min_frequency]
    
    # Sort by count
    filtered.sort(key=lambda x: x[1], reverse=True)
    
    return filtered[:top_n]


def extract_bigrams(
    problems: List[Dict],
    top_n: int = 30,
    min_frequency: int = 2
) -> List[Tuple[str, int]]:
    """Extract common two-word phrases"""
    
    all_bigrams = []
    
    for problem in problems:
        text = f"{problem.get('title', '')} {problem.get('content', '')}"
        tokens = tokenize(text)
        tokens = [t for t in tokens if t not in STOP_WORDS]
        
        # Create bigrams
        for i in range(len(tokens) - 1):
            bigram = f"{tokens[i]} {tokens[i+1]}"
            all_bigrams.append(bigram)
    
    counter = Counter(all_bigrams)
    filtered = [(bg, count) for bg, count in counter.items() 
                if count >= min_frequency]
    filtered.sort(key=lambda x: x[1], reverse=True)
    
    return filtered[:top_n]


def categorize_problems(problems: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Categorize problems by industry/topic.
    Returns dict of category -> list of problems.
    """
    
    categorized = {cat: [] for cat in CATEGORY_KEYWORDS}
    categorized['other'] = []
    
    for problem in problems:
        text = f"{problem.get('title', '')} {problem.get('content', '')}".lower()
        
        matched_categories = []
        
        for category, keywords in CATEGORY_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                matched_categories.append(category)
        
        if matched_categories:
            # Add to primary category (first match)
            primary = matched_categories[0]
            problem_copy = problem.copy()
            problem_copy['categories'] = matched_categories
            categorized[primary].append(problem_copy)
        else:
            categorized['other'].append(problem)
    
    # Remove empty categories
    return {k: v for k, v in categorized.items() if v}


def calculate_problem_score(problem: Dict) -> float:
    """
    Calculate a "problem intensity" score based on language.
    Higher score = more frustrated user = bigger opportunity.
    """
    
    text = f"{problem.get('title', '')} {problem.get('content', '')}".lower()
    tokens = tokenize(text)
    
    # Base score from engagement
    engagement_score = problem.get('score', 0) + problem.get('comments', 0)
    
    # Problem indicator presence
    indicator_count = sum(1 for t in tokens if t in PROBLEM_INDICATORS)
    indicator_score = indicator_count * 5
    
    # Exclamation marks indicate frustration
    exclamation_score = text.count('!') * 2
    
    # Question marks indicate need
    question_score = text.count('?') * 1
    
    # All caps words indicate frustration
    caps_words = len(re.findall(r'\b[A-Z]{3,}\b', problem.get('content', '')))
    caps_score = caps_words * 3
    
    # Combine scores
    total = engagement_score + indicator_score + exclamation_score + question_score + caps_score
    
    return total


def rank_problems_by_opportunity(problems: List[Dict]) -> List[Dict]:
    """
    Rank problems by startup opportunity potential.
    """
    
    for problem in problems:
        problem['opportunity_score'] = calculate_problem_score(problem)
    
    # Sort by opportunity score
    ranked = sorted(problems, key=lambda x: x.get('opportunity_score', 0), reverse=True)
    
    return ranked


def generate_keyword_report(problems: List[Dict]) -> str:
    """Generate a text report of keyword analysis"""
    
    lines = []
    lines.append("=" * 50)
    lines.append("KEYWORD ANALYSIS REPORT")
    lines.append("=" * 50)
    
    # Top keywords
    keywords = extract_keywords(problems, top_n=30)
    lines.append("\nTOP KEYWORDS:")
    lines.append("-" * 30)
    for word, count in keywords[:20]:
        lines.append(f"  {word}: {count}")
    
    # Top phrases
    bigrams = extract_bigrams(problems, top_n=20)
    lines.append("\nTOP PHRASES:")
    lines.append("-" * 30)
    for phrase, count in bigrams[:15]:
        lines.append(f"  {phrase}: {count}")
    
    # Categories
    categorized = categorize_problems(problems)
    lines.append("\nPROBLEMS BY CATEGORY:")
    lines.append("-" * 30)
    for cat, items in sorted(categorized.items(), key=lambda x: -len(x[1])):
        lines.append(f"  {cat}: {len(items)}")
    
    return "\n".join(lines)