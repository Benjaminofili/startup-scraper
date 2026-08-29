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
noise instead of forcing them into a nearest cluster) on L2-normalized
embeddings, so euclidean distance behaves like cosine similarity -
clustering on raw, unnormalized vectors lets magnitude differences
dominate and tends to produce a couple of giant, incoherent "everything
is vaguely tech" blobs rather than tight problem-specific groups.

min_cluster_size scales with corpus size (see MIN_CLUSTER_FRACTION
below) instead of being a fixed small constant - a fixed
min_cluster_size=4 with default min_samples on a few hundred docs is
permissive enough that HDBSCAN chains loosely-related documents into a
couple of huge clusters instead of many small coherent ones (seen in
practice: run #1 produced 2 clusters covering 440/491 docs). min_samples
is kept below min_cluster_size (the standard relationship - min_samples
> min_cluster_size was tried and made the density estimate so
conservative it found zero clusters at all: run #2, 0/490).

Usage:
    python -m problem_radar.cluster
"""

import json
import os

import numpy as np

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CORPUS_PATH = os.path.join(DATA_DIR, "corpus.json")
CLUSTERS_PATH = os.path.join(DATA_DIR, "clusters.json")

MIN_CLUSTER_SIZE_FLOOR = 5
MIN_CLUSTER_FRACTION = 0.012   # ~6 for a 500-doc corpus
MIN_SAMPLES_FLOOR = 3
MIN_SAMPLES_RATIO = 0.5        # min_samples = min_cluster_size * this (kept < min_cluster_size)


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
        vectors, backend = embed_fastembed(texts)
    except Exception as e:
        print(f"fastembed unavailable ({type(e).__name__}: {e}); falling back to TF-IDF")
        vectors, backend = embed_tfidf(texts)

    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vectors / norms, backend


def cluster(vectors):
    from sklearn.cluster import HDBSCAN

    n = len(vectors)
    min_cluster_size = max(MIN_CLUSTER_SIZE_FLOOR, round(n * MIN_CLUSTER_FRACTION))
    min_samples = max(MIN_SAMPLES_FLOOR, round(min_cluster_size * MIN_SAMPLES_RATIO))
    print(f"HDBSCAN: min_cluster_size={min_cluster_size}, min_samples={min_samples}")

    model = HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric="euclidean",
    )
    labels = model.fit_predict(vectors)
    return labels, min_cluster_size, min_samples


def main():
    corpus = load_corpus()
    docs = corpus["docs"]
    if len(docs) < MIN_CLUSTER_SIZE_FLOOR * 2:
        raise SystemExit(
            f"Only {len(docs)} docs in corpus.json - run `python -m problem_radar.fetch` first."
        )

    texts = [f"{d['title']}\n{d['content']}" for d in docs]
    print(f"Embedding {len(texts)} docs...")
    vectors, backend = embed(texts)

    print("Clustering...")
    labels, min_cluster_size, min_samples = cluster(vectors)

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
        "min_cluster_size": min_cluster_size,
        "min_samples": min_samples,
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
