# scraper/utils/health.py
"""
Per-collector health registry.

A source's total count hides partial failure (e.g. Reddit "17 posts" was
entirely the RSS fallback while every search.json request returned 403).
Collectors record their own status here and main.py persists it.

Status rules:
  healthy  - requests succeeded and returned data
  low_coverage - requests succeeded but most targets returned nothing
  degraded - some requests failed, or succeeded but returned nothing
  failed   - every request failed / collector unusable
  disabled - intentionally excluded
"""

from typing import Dict, Optional

_REGISTRY: Dict[str, Dict] = {}


def record(collector: str, count: int, attempts: int = 0, errors: int = 0,
           error: Optional[str] = None, disabled: bool = False,
           empty_results: int = 0) -> str:
    """
    attempts       - requests/targets tried
    errors         - requests that actually FAILED (HTTP error, exception)
    empty_results  - requests that succeeded but returned nothing useful
    A successful-but-empty response is not a failure: it means the
    watchlist/queries are producing poor coverage, which is a different
    problem from a broken scraper.
    """
    successful = max(attempts - errors, 0)
    if disabled:
        status = "disabled"
    elif attempts > 0 and errors >= attempts:
        status = "failed"
    elif errors > 0 or count == 0:
        status = "degraded"
    elif attempts > 0 and empty_results * 2 >= attempts:
        status = "low_coverage"
    else:
        status = "healthy"
    _REGISTRY[collector] = {
        "status": status, "attempts": attempts,
        "successful_requests": successful, "request_errors": errors,
        "empty_results": empty_results, "items_collected": count, "error": error,
    }
    if status != "healthy" and status != "disabled":
        import os
        msg = (f"{collector}: {status} (items={count}, requests ok={successful}/{attempts}, "
               f"errors={errors}, empty={empty_results}" + (f", {error}" if error else "") + ")")
        print(f"   ⚠️ HEALTH {msg}")
        if os.getenv("GITHUB_ACTIONS"):
            print(f"::warning title=Source health::{msg}")
    return status


def snapshot() -> Dict[str, Dict]:
    return dict(_REGISTRY)


def reset():
    _REGISTRY.clear()
