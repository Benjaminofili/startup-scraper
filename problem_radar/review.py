# problem_radar/review.py
"""
Turn clusters.json into a human-readable review sheet.

This is the actual output of the experiment - there is no dashboard and
no scoring on purpose (see problem_radar/README.md). The only question
this file exists to help you answer, per cluster, is:

    1. Coherent?        Do these documents actually belong together?
    2. Expected by me?  Would I have grouped these myself, e.g. by
                         searching for an obvious shared keyword?
    3. Surprising?       Did it surface a connection you wouldn't have
                         made yourself - different wording, different
                         source, same underlying problem?
    4. Notes             What's the underlying problem, in your words?
                         Would you investigate it further?

Coherent-but-not-surprising clusters mean the clustering agrees with
your intuition, which is fine but not evidence it beats manual search.
Coherent-and-surprising clusters are the actual signal that embedding-
based discovery is finding something a keyword search would miss.

Usage:
    python -m problem_radar.review
"""

import json
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CORPUS_PATH = os.path.join(DATA_DIR, "corpus.json")
CLUSTERS_PATH = os.path.join(DATA_DIR, "clusters.json")
REVIEW_PATH = os.path.join(DATA_DIR, "review.md")


def main():
    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        corpus = json.load(f)
    with open(CLUSTERS_PATH, "r", encoding="utf-8") as f:
        clusters = json.load(f)

    docs_by_id = {d["doc_id"]: d for d in corpus["docs"]}

    lines = []
    lines.append("# Problem Radar - Cluster Review\n")
    lines.append(f"- Corpus fetched: {corpus['fetched_at']}")
    lines.append(f"- Total docs: {corpus['total_docs']} ({corpus['sources']})")
    lines.append(f"- Embedding backend: {clusters['embedding_backend']}")
    lines.append(
        f"- {clusters['num_clusters']} clusters, "
        f"{clusters['num_noise']} unclustered (noise) docs\n"
    )
    lines.append(
        "For each cluster below, fill in Coherent? / Expected by me? / "
        "Surprising? / Notes by hand. See the module docstring in "
        "review.py for what each question means. The clusters that "
        "matter most are Coherent=yes + Surprising=yes - those are the "
        "evidence that this beats manually scanning the same sources.\n"
    )
    lines.append("---\n")

    for c in clusters["clusters"]:
        lines.append(f"## Cluster {c['cluster_id']} - {c['size']} docs\n")
        lines.append("- Coherent? [ ]")
        lines.append("- Expected by me? [ ]")
        lines.append("- Surprising? [ ]")
        lines.append("- Notes / underlying problem:\n")
        lines.append("| Source | Author | Title | Score | URL |")
        lines.append("|---|---|---|---|---|")
        for doc_id in c["doc_ids"]:
            d = docs_by_id.get(doc_id)
            if not d:
                continue
            title = d["title"].replace("|", "/").replace("\n", " ")
            author = d.get("author", "") or ""
            lines.append(
                f"| {d['source']} ({d['subsource']}) | {author} | {title} "
                f"| {d.get('score', '')} | {d['url']} |"
            )
        lines.append("")

    if clusters["num_noise"]:
        lines.append("---\n")
        lines.append(
            f"## Unclustered (noise) - {clusters['num_noise']} docs\n\n"
            "Docs HDBSCAN couldn't confidently place in any cluster - "
            "one-off topics, or too few similar docs in this corpus to "
            "form a group. Worth a skim but not the primary output.\n"
        )

    with open(REVIEW_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Wrote {REVIEW_PATH}")
    print("Open it and work through each cluster by hand.")


if __name__ == "__main__":
    main()
