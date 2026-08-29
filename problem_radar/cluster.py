# problem_radar/cluster.py
"""
Embed and cluster the corpus fetched by fetch.py.

This is the part of the Problem Radar experiment that actually matters:
everything downstream (evidence provenance, "did this surface something
I wouldn't have grouped myself") depends on whether semantic clustering
of complaint/discussion text produces coherent, non-trivial groups.

Embedding backend:
  - Primary: fastembed (BAAI/bge-small-en-v1.5, ONNX, no torch needed).
    Downloads the model from Hugging Face on first run.
  - Fallback: TF-IDF + TruncatedSVD (scikit-learn only, no downloads).
    Used automatically if fastembed / the model download isn't
    available (e.g. a network-restricted environment). This only
    captures lexical overlap, not paraphrase-level similarity, so
    clusters from the fallback should be trusted less - the corpus.json
    -> clusters.json output notes which backend produced them.

Clustering: sklearn's HDBSCAN (density-based, no need to pick a cluster
count up front, and it explicitly labels sparse/one-off documents as
noise instead of forcing them into a nearest cluster).

Usage:
    python -m problem_radar.cluster
"""

import json
import os

import numpy as np

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CORPUS_PATH = os.path.join(DATA_DIR, "corpus.json")
CLUSTERS_PATH = os.path.join(DATA_DIR, "clusters.json")

MIN_CLUSTER_SIZE = 4


def load_corpus():
    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def embed_fastembed(texts):
    from fastembed import TextEmbedding

    model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    vectors = np.array(list(model.embed(texts)))
    return vectors, "fastembed:BAAI/bge-small-en-v1.5"


def embed_tfidf(texts):
    from sklearn.decomposition import TruncatedSVD
    from sklearn.feature_extraction.text import TfidfVectorizer

    tfidf = TfidfVectorizer(max_features=5000, stop_words="english", min_df=2)
    matrix = tfidf.fit_transform(texts)
    n_components = min(100, matrix.shape[1] - 1, matrix.shape[0] - 1)
    svd = TruncatedSVD(n_components=max(n_components, 2), random_state=42)
    vectors = svd.fit_transform(matrix)
    return vectors, "tfidf+svd (fallback - no HF access, lexical overlap only)"


def embed(texts):
    try:
        return embed_fastembed(texts)
    except Exception as e:
        print(f"fastembed unavailable ({type(e).__name__}: {e}); falling back to TF-IDF")
        return embed_tfidf(texts)


def cluster(vectors):
    from sklearn.cluster import HDBSCAN

    model = HDBSCAN(min_cluster_size=MIN_CLUSTER_SIZE, metric="euclidean")
    labels = model.fit_predict(vectors)
    return labels


def main():
    corpus = load_corpus()
    docs = corpus["docs"]
    if len(docs) < MIN_CLUSTER_SIZE * 2:
        raise SystemExit(
            f"Only {len(docs)} docs in corpus.json - run `python -m problem_radar.fetch` "
            "first, or lower MIN_CLUSTER_SIZE for a tiny test run."
        )

    texts = [f"{d['title']}\n{d['content']}" for d in docs]
    print(f"Embedding {len(texts)} docs...")
    vectors, backend = embed(texts)

    print("Clustering...")
    labels = cluster(vectors)

    clusters = {}
    noise = []
    for doc, label in zip(docs, labels):
        if label == -1:
            noise.append(doc["doc_id"])
            continue
        clusters.setdefault(int(label), []).append(doc["doc_id"])

    cluster_list = [
        {
            "cluster_id": cid,
            "size": len(doc_ids),
            "doc_ids": doc_ids,
            # Filled in later, by hand, in review.md - not computed here.
            "coherent": None,
            "expected_by_me": None,
            "surprising": None,
            "notes": "",
        }
        for cid, doc_ids in sorted(clusters.items(), key=lambda kv: -len(kv[1]))
    ]

    out = {
        "embedding_backend": backend,
        "min_cluster_size": MIN_CLUSTER_SIZE,
        "total_docs": len(docs),
        "num_clusters": len(cluster_list),
        "num_noise": len(noise),
        "noise_doc_ids": noise,
        "clusters": cluster_list,
    }
    with open(CLUSTERS_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    print(f"\n{len(cluster_list)} clusters, {len(noise)} noise docs (backend: {backend})")
    print(f"Wrote {CLUSTERS_PATH}")
    print("Next: python -m problem_radar.review")


if __name__ == "__main__":
    main()
