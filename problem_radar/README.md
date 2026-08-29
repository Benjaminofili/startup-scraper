# Problem Radar

A bounded experiment, not a rebuild of the scraper. It exists to answer one
question before any more engineering time goes into "opportunity discovery":

> Can semantic clustering of real conversations surface problems worth
> investigating - including ones I wouldn't have found by manually
> searching the same sources?

It is intentionally not: another data source, a feasibility/opportunity
score, or a dashboard. Those all assume clustering already works. This
proves or disproves that first, cheaply.

## Why this exists

The scraper in `scraper/` (feasibility_scorer.py, ai_analyzer.py, 8
sources) treats every scraped item independently and asks an LLM to turn
raw posts into scored startup ideas directly. That skips the actual hard
problem: knowing whether "37 different-looking posts" are 37 different
problems or the same problem said 37 different ways, and being able to
trace any conclusion back to the specific evidence behind it.

Problem Radar does three things, in order, and stops:

1. **Fetch** a one-time snapshot of a few hundred Reddit + Hacker News
   posts (the only two sources here with a real, free, unauthenticated
   API - see `fetch.py`).
2. **Cluster** them by embedding similarity (not keyword overlap) so
   paraphrased complaints about the same problem end up in the same
   group, and one-off unrelated posts get correctly excluded as noise.
3. **Generate a review sheet** with full evidence (source, author,
   title, URL) per cluster, and blank fields for you to judge each
   cluster by hand.

No score is computed for you. See "What this deliberately doesn't do"
below for why.

## Running it

```bash
pip install -r problem_radar/requirements.txt

python -m problem_radar.fetch     # -> problem_radar/data/corpus.json
python -m problem_radar.cluster   # -> problem_radar/data/clusters.json
python -m problem_radar.review    # -> problem_radar/data/review.md
```

Then open `problem_radar/data/review.md` and work through each cluster.

None of this runs in CI or the scheduled scrape workflow - it's a manual,
one-shot research tool. `problem_radar/data/` is gitignored; each run
produces its own local snapshot.

Fetching takes a few minutes (rate-limited on purpose, to stay polite to
Reddit/HN). Clustering needs `fastembed`, which downloads a small ONNX
model from Hugging Face on first run - if that's blocked in your
environment, `cluster.py` automatically falls back to TF-IDF + SVD
(scikit-learn only, no downloads) and labels the output accordingly in
`clusters.json` and `review.md` so you know which one you're looking at.
Trust TF-IDF clusters less: they only catch shared wording, not
paraphrases like "losing WhatsApp orders" vs. "can't track customer
orders from WhatsApp" - the embedding backend is what's actually being
tested here.

## Judging the output - the four questions

For every cluster in `review.md`:

1. **Coherent?** Do these documents actually belong together, or did the
   algorithm force unrelated things into one bucket?
2. **Expected by me?** Would you have grouped these yourself - e.g. by
   searching one obvious keyword?
3. **Surprising?** Did it connect posts you wouldn't have linked
   yourself - different wording, different source, same underlying
   problem?
4. **Notes** - what's the underlying problem, in your own words? Would
   you seriously consider investigating it further?

**Coherent + expected** clusters mean the algorithm agrees with your
intuition - fine, but not evidence it beats manually scanning Reddit.
**Coherent + surprising** clusters are the actual signal that this is
worth building on. If every coherent cluster is also something you'd
have found by keyword search, that's a real result too - it means
clustering isn't adding much here yet, and the honest move is to stop
rather than keep layering scoring and a dashboard on top of it.

## What this deliberately doesn't do (and why)

- **No feasibility/opportunity score.** The previous scraper's
  `feasibility_scorer.py` produced numbers like "90/100" that mixed
  measured facts (how many docs mention this) with LLM guesses (market
  size, willingness to pay) into one composite, with no way to tell
  which was which. A fake-precise score you can't audit is worse than
  no score - it launders a guess into something that looks like data.
- **No dashboard.** A UI is worth building once there's something worth
  displaying. Right now the only consumer of this output is you, once,
  reading a markdown file.
- **Two sources, not eight.** Reddit and HN both have free, stable,
  unauthenticated APIs and rich complaint-style language. Every other
  source in `scraper/sources/` either needs auth, breaks often (the
  git log here has multiple "replace dead data sources" commits), or
  adds coverage without helping answer the clustering question.
- **No Nigeria filter.** Global signal first; whether a cluster has a
  distinctly Nigerian angle is one of the judgment calls you make by
  hand while reading the evidence, not something baked into the fetch.

## Success condition

Not "N clusters found" or "N opportunities generated." The bar is:

> At least one cluster is coherent, surprising, and compelling enough
> that you would seriously consider investigating or building for it.

If that happens, evidence-linked clustering is worth investing further
in (better clustering, more sources, then - only then - a scoring
layer). If it doesn't happen after a real attempt, that's a useful
result too: it means the effort belongs elsewhere, and the existing
`scraper/` pipeline shouldn't get more layers built on top of its
current per-item LLM scoring either.
