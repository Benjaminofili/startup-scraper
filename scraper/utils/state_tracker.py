# scraper/utils/state_tracker.py

import json
import os

STATE_DIR = "data"
SEEN_IDS_PATH = f"{STATE_DIR}/seen_ids.json"
ROTATION_PATH = f"{STATE_DIR}/rotation_state.json"

# Keep the seen-ID set from growing forever - old repo commits still have
# the full history if you ever need it, this just bounds file size / git diff.
MAX_SEEN_IDS = 20000


def _ensure_state_dir():
    os.makedirs(STATE_DIR, exist_ok=True)


def load_seen_ids() -> set:
    """Load the set of unique_ids seen in any previous run."""
    if not os.path.exists(SEEN_IDS_PATH):
        return set()
    try:
        with open(SEEN_IDS_PATH, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_seen_ids(ids: set):
    """Persist the seen-ID set, trimmed to the most recent MAX_SEEN_IDS."""
    _ensure_state_dir()
    ids_list = list(ids)
    if len(ids_list) > MAX_SEEN_IDS:
        # Keep the tail (most recently added) - dicts/sets preserve insertion
        # order in practice here since callers pass in scrape order, but to
        # be safe just truncate arbitrarily; exact recency isn't critical.
        ids_list = ids_list[-MAX_SEEN_IDS:]
    with open(SEEN_IDS_PATH, "w", encoding="utf-8") as f:
        json.dump(ids_list, f)


def filter_new(problems: list, seen_ids: set) -> list:
    """Return only problems whose unique_id hasn't been seen in a prior run."""
    return [p for p in problems if p.get("unique_id") not in seen_ids]


def get_rotation_slice(pool: list, chunk_size: int, state_key: str) -> list:
    """
    Return a rotating slice of `pool`, advancing one chunk further each
    time this is called with the same state_key across runs. This is how
    a fixed-looking query/repo list actually covers different ground over
    successive scheduled runs instead of hammering the same subset forever.
    """
    _ensure_state_dir()
    state = {}
    if os.path.exists(ROTATION_PATH):
        try:
            with open(ROTATION_PATH, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            state = {}

    start = state.get(state_key, 0) % len(pool)
    end = start + chunk_size

    if end <= len(pool):
        chunk = pool[start:end]
    else:
        # wrap around
        chunk = pool[start:] + pool[: end - len(pool)]

    state[state_key] = (start + chunk_size) % len(pool)

    with open(ROTATION_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f)

    return chunk
