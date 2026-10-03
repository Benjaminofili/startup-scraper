# scraper/utils/health.py
"""
Per-collector health registry.

A source's total count hides partial failure (e.g. Reddit "17 posts" was
entirely the RSS fallback while every search.json request returned 403).
Collectors record their own status here and main.py persists it.

Status rules:
  healthy  - requests succeeded and returned data
  degraded - some requests failed, or succeeded but returned nothing
  failed   - every request failed / collector unusable
  disabled - intentionally excluded
"""

from typing import Dict, Optional

_REGISTRY: Dict[str, Dict] = {}


def record(collector: str, count: int, attempts: int = 0, errors: int = 0,
           error: Optional[str] = None, disabled: bool = False) -> str:
    if disabled:
        status = "disabled"
    elif attempts > 0 and errors >= attempts:
        status = "failed"
    elif errors > 0 or count == 0:
        status = "degraded"
    else:
        status = "healthy"
    _REGISTRY[collector] = {
        "status": status, "count": count, "attempts": attempts,
        "errors": errors, "error": error,
    }
    if status in ("failed", "degraded"):
        import os
        msg = f"{collector}: {status} (count={count}, errors={errors}/{attempts}" + (f", {error}" if error else "") + ")"
        print(f"   ⚠️ HEALTH {msg}")
        if os.getenv("GITHUB_ACTIONS"):
            print(f"::warning title=Source health::{msg}")
    return status


def snapshot() -> Dict[str, Dict]:
    return dict(_REGISTRY)


def reset():
    _REGISTRY.clear()
