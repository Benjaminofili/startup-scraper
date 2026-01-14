# scraper/utils/deduplicator.py

import hashlib
import re
from typing import List, Dict


def normalize_text(text: str) -> str:
    """Normalize text for comparison"""
    if not text:
        return ""
    
    # Lowercase
    text = text.lower()
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove special characters
    text = re.sub(r'[^\w\s]', '', text)
    
    return text.strip()


def create_content_hash(problem: Dict) -> str:
    """Create a unique hash for a problem based on content"""
    
    # Combine source + normalized content for uniqueness
    source = problem.get('source', '')
    title = normalize_text(problem.get('title', ''))
    content = normalize_text(problem.get('content', ''))
    
    # Use first 150 chars of content to allow slight variations
    combined = f"{source}:{title[:100]}:{content[:150]}"
    
    return hashlib.md5(combined.encode()).hexdigest()


def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate simple similarity ratio between two texts"""
    
    if not text1 or not text2:
        return 0.0
    
    text1 = normalize_text(text1)
    text2 = normalize_text(text2)
    
    # Simple word overlap similarity
    words1 = set(text1.split())
    words2 = set(text2.split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1 & words2
    union = words1 | words2
    
    return len(intersection) / len(union)


def deduplicate_problems(problems: List[Dict], similarity_threshold: float = 0.85) -> List[Dict]:
    """
    Remove duplicate problems using multiple strategies:
    1. Exact unique_id match
    2. Content hash match
    3. High similarity match
    """
    
    if not problems:
        return []
    
    seen_ids = set()
    seen_hashes = set()
    unique_problems = []
    
    for problem in problems:
        # Strategy 1: Check unique_id
        uid = problem.get('unique_id')
        if uid and uid in seen_ids:
            continue
        
        # Strategy 2: Check content hash
        content_hash = create_content_hash(problem)
        if content_hash in seen_hashes:
            continue
        
        # Strategy 3: Check similarity with recent items (expensive, limit scope)
        is_similar = False
        content = problem.get('content', problem.get('title', ''))
        
        # Only check against last 50 items for performance
        for existing in unique_problems[-50:]:
            existing_content = existing.get('content', existing.get('title', ''))
            
            if calculate_similarity(content, existing_content) > similarity_threshold:
                is_similar = True
                break
        
        if is_similar:
            continue
        
        # Not a duplicate - add it
        if uid:
            seen_ids.add(uid)
        seen_hashes.add(content_hash)
        unique_problems.append(problem)
    
    return unique_problems


def merge_duplicates(problems: List[Dict]) -> List[Dict]:
    """
    Instead of removing duplicates, merge them to show cross-platform validation.
    If same problem appears on Reddit AND Nairaland, it's more validated.
    """
    
    merged = {}
    
    for problem in problems:
        content_hash = create_content_hash(problem)
        
        if content_hash in merged:
            # Merge: combine sources, add scores
            existing = merged[content_hash]
            
            # Track all sources
            if 'all_sources' not in existing:
                existing['all_sources'] = [existing['source']]
            existing['all_sources'].append(problem['source'])
            
            # Add scores
            existing['score'] = existing.get('score', 0) + problem.get('score', 0)
            
            # Mark as validated across platforms
            existing['cross_validated'] = True
            existing['validation_count'] = len(existing['all_sources'])
        else:
            problem['cross_validated'] = False
            problem['validation_count'] = 1
            merged[content_hash] = problem
    
    # Sort by validation count (cross-platform problems are more valuable)
    result = list(merged.values())
    result.sort(key=lambda x: (x.get('validation_count', 1), x.get('score', 0)), reverse=True)
    
    return result