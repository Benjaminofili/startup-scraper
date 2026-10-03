# scraper/utils/state_tracker.py

import json
import os
from datetime import datetime, timezone

STATE_DIR = "data"
SEEN_IDS_PATH = f"{STATE_DIR}/seen_ids.json"
ROTATION_PATH = f"{STATE_DIR}/rotation_state.json"

# Keep the seen-ID set from growing forever - old repo commits still have
# the full history if you ever need it, this just bounds file size / git diff.
MAX_SEEN_IDS = 20000


def _ensure_state_dir():
    os.makedirs(STATE_DIR, exist_ok=True)


def _load_seen_records() -> dict:
    """Return {unique_id: last_seen_iso_date}. Accepts the legacy plain-list format."""
    if not os.path.exists(SEEN_IDS_PATH):
        return {}
    try:
        with open(SEEN_IDS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}
    if isinstance(data, dict):
        return data
    # Legacy format: bare list with no chronology. Stamp as "unknown-old"
    # so these are the first to be evicted when the cap is hit.
    return {i: "0000-00-00" for i in data}


def load_seen_ids() -> set:
    """Load the set of unique_ids seen in any previous run."""
    return set(_load_seen_records())


def save_seen_ids(ids: set):
    """
    Persist seen IDs with a last-seen date. Previously-known IDs keep their
    stamp; IDs new to this call get today's date. When over MAX_SEEN_IDS the
    oldest-stamped are evicted (a set has no insertion order, so recency has
    to be stored explicitly).
    """
    _ensure_state_dir()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    records = _load_seen_records()
    for i in ids:
        records[i] = today if i not in records or records[i] == "0000-00-00" else records[i]
    # Refresh last_seen for IDs observed again this run is done by caller
    # passing the full union; keep prior stamp otherwise.
    if len(records) > MAX_SEEN_IDS:
        keep = sorted(records.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)[:MAX_SEEN_IDS]
        records = dict(keep)
    with open(SEEN_IDS_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, sort_keys=True)


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
