# scraper/utils/normalize.py
"""
Cross-source signal normalization and stratified sampling.

Raw `score` means different things per source (HN points, Reddit upvotes,
Play Store thumbs-up, GitHub reactions, a synthetic Trends rank), so it is
never comparable across sources. We keep it as `raw_score` and rank by
`signal`: the item's percentile within its own source (0-1).
"""

from collections import defaultdict
from typing import Dict, List

# Sources whose `score` is a rank/ordinal, not a measure of engagement.
# They get a neutral signal so they neither crowd out nor get buried.
NEUTRAL_SIGNAL_SOURCES = {"GoogleTrends"}


def add_signal(problems: List[Dict]) -> List[Dict]:
    """Annotate each problem with `raw_score` and a per-source percentile `signal`."""
    by_source = defaultdict(list)
    for p in problems:
        p.setdefault("raw_score", p.get("score", 0) or 0)
        by_source[p.get("source", "Unknown")].append(p)

    for source, items in by_source.items():
        if source in NEUTRAL_SIGNAL_SOURCES or len(items) == 1:
            for p in items:
                p["signal"] = 0.5
            continue
        ordered = sorted(items, key=lambda x: x["raw_score"])
        n = len(ordered)
        # Ties share the average percentile so equal scores rank equally.
        i = 0
        while i < n:
            j = i
            while j + 1 < n and ordered[j + 1]["raw_score"] == ordered[i]["raw_score"]:
                j += 1
            pct = ((i + j) / 2) / (n - 1)
            for k in range(i, j + 1):
                ordered[k]["signal"] = round(pct, 4)
            i = j + 1
    return problems


def stratified_sample(problems: List[Dict], n: int) -> List[Dict]:
    """
    Take up to n problems round-robin across sources, highest `signal`
    first within each source, so no single source's scale can dominate.
    """
    by_source = defaultdict(list)
    for p in problems:
        by_source[p.get("source", "Unknown")].append(p)
    for items in by_source.values():
        items.sort(key=lambda x: x.get("signal", 0), reverse=True)

    picked: List[Dict] = []
    queues = list(by_source.values())
    idx = 0
    while len(picked) < n and any(queues):
        for q in queues:
            if idx < len(q) and len(picked) < n:
                picked.append(q[idx])
        idx += 1
        if idx > max(len(q) for q in queues):
            break
    return picked
