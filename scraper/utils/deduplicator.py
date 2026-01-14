# scraper/analyzers/keyword_extractor.py

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
    'there', 'then', 'once', 'if', 'about', 'into', 'through', 'during',
    'before', 'after', 'above', 'below', 'between', 'under', 'again',
    'app', 'use', 'using', 'used', 'want', 'need', 'dont', 'cant', 'im',
    'ive', 'thats', 'get', 'got', 'like', 'really', 'even', 'still',
}

# Category keywords
CATEGORY_KEYWORDS = {
    'fintech': ['payment', 'bank', 'money', 'transfer', 'wallet', 'loan',
                'credit', 'pos', 'atm', 'opay', 'palmpay', 'kuda', 'moniepoint'],
    'ecommerce': ['shop', 'buy', 'sell', 'order', 'delivery', 'shipping',
                  'product', 'store', 'jumia', 'konga'],
    'logistics': ['delivery', 'shipping', 'tracking', 'driver', 'rider',
                  'dispatch', 'bolt', 'uber'],
    'education': ['learn', 'course', 'student', 'school', 'study', 'exam',
                  'jamb', 'waec'],
    'jobs': ['job', 'work', 'hire', 'salary', 'career', 'remote', 'freelance'],
}


def tokenize(text: str) -> List[str]:
    """Split text into words"""
    if not text:
        return []
    
    text = text.lower()
    text = re.sub(r'http\S+|www\S+', '', text)
    text = re.sub(r"[^a-zA-Z0-9'\s]", ' ', text)
    tokens = text.split()
    tokens = [t.strip("'") for t in tokens if len(t) > 2]
    
    return tokens


def extract_keywords(problems: List[Dict], top_n: int = 30) -> List[Tuple[str, int]]:
    """Extract most common keywords"""
    
    all_tokens = []
    
    for problem in problems:
        text = f"{problem.get('title', '')} {problem.get('content', '')}"
        tokens = tokenize(text)
        tokens = [t for t in tokens if t not in STOP_WORDS]
        all_tokens.extend(tokens)
    
    counter = Counter(all_tokens)
    
    return counter.most_common(top_n)


def categorize_problems(problems: List[Dict]) -> Dict[str, List[Dict]]:
    """Categorize problems by industry"""
    
    categorized = {cat: [] for cat in CATEGORY_KEYWORDS}
    categorized['other'] = []
    
    for problem in problems:
        text = f"{problem.get('title', '')} {problem.get('content', '')}".lower()
        
        matched = False
        for category, keywords in CATEGORY_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                categorized[category].append(problem)
                matched = True
                break
        
        if not matched:
            categorized['other'].append(problem)
    
    return {k: v for k, v in categorized.items() if v}