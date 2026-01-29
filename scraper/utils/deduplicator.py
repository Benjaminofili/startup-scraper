# scraper/utils/deduplicator.py

from typing import List, Dict, Set
from difflib import SequenceMatcher


def similarity_ratio(text1: str, text2: str) -> float:
    """Calculate similarity ratio between two texts"""
    if not text1 or not text2:
        return 0.0
    return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()


def is_duplicate(problem1: Dict, problem2: Dict, threshold: float = 0.85) -> bool:
    """
    Check if two problems are duplicates based on title and content similarity
    
    Args:
        problem1: First problem dict with 'title' and 'content' keys
        problem2: Second problem dict with 'title' and 'content' keys
        threshold: Similarity threshold (0.0 to 1.0)
    
    Returns:
        True if problems are considered duplicates
    """
    title1 = problem1.get('title', '').strip()
    title2 = problem2.get('title', '').strip()
    
    # Check title similarity
    title_sim = similarity_ratio(title1, title2)
    
    if title_sim >= threshold:
        return True
    
    # Check content similarity if titles are somewhat similar
    if title_sim >= 0.6:
        content1 = problem1.get('content', '').strip()
        content2 = problem2.get('content', '').strip()
        
        content_sim = similarity_ratio(content1, content2)
        
        if content_sim >= threshold:
            return True
    
    return False


def deduplicate_problems(problems: List[Dict], threshold: float = 0.85) -> List[Dict]:
    """
    Remove duplicate problems from a list
    
    Args:
        problems: List of problem dictionaries
        threshold: Similarity threshold for considering duplicates (0.0 to 1.0)
    
    Returns:
        List of unique problems, preserving the highest-scored version of duplicates
    """
    if not problems:
        return []
    
    # Sort by score (highest first) to keep best versions
    sorted_problems = sorted(
        problems, 
        key=lambda x: x.get('score', 0), 
        reverse=True
    )
    
    unique_problems = []
    seen_indices: Set[int] = set()
    
    for i, problem in enumerate(sorted_problems):
        if i in seen_indices:
            continue
        
        # Add this problem to unique list
        unique_problems.append(problem)
        
        # Mark similar problems as seen
        for j in range(i + 1, len(sorted_problems)):
            if j not in seen_indices:
                if is_duplicate(problem, sorted_problems[j], threshold):
                    seen_indices.add(j)
    
    return unique_problems