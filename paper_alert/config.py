from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

from .constants import BIORXIV_LOOKBACK, DEFAULT_KEYWORDS, MAX_RESULTS_PER_SOURCE

DEFAULT_SOURCES = (
    "arxiv",
    "pubmed",
    "biorxiv",
    "medrxiv",
    "crossref",
    "semanticscholar",
)


@dataclass(slots=True)
class PaperAlertConfig:
    keywords: Tuple[str, ...]
    sources: Tuple[str, ...]
    max_results: int
    store_path: Path
    biorxiv_lookback_days: int
    semanticscholar_api_key: str | None

    @classmethod
    def from_env(cls) -> "PaperAlertConfig":
        keywords = _load_keywords(os.getenv("PAPER_ALERT_KEYWORDS"))
        sources = _load_sources(os.getenv("PAPER_ALERT_SOURCES"))
        max_results = _load_int_env(
            "PAPER_ALERT_MAX_RESULTS",
            default=MAX_RESULTS_PER_SOURCE,
            minimum=1,
        )
        store_env = os.getenv("PAPER_ALERT_STORE")
        store_path = Path(store_env).expanduser() if store_env else Path.home() / ".paper_alert_seen.json"
        lookback_days = _load_int_env(
            "PAPER_ALERT_LOOKBACK_DAYS",
            default=BIORXIV_LOOKBACK.days,
            minimum=0,
        )
        api_key = os.getenv("PAPER_ALERT_SEMANTIC_SCHOLAR_KEY")
        return cls(
            keywords=keywords,
            sources=sources,
            max_results=max_results,
            store_path=store_path,
            biorxiv_lookback_days=lookback_days,
            semanticscholar_api_key=api_key,
        )

    @property
    def biorxiv_lookback(self):
        from datetime import timedelta

        return timedelta(days=self.biorxiv_lookback_days)


def _load_keywords(raw: str | None) -> Tuple[str, ...]:
    if raw:
        items = [item.strip() for item in raw.split(",") if item.strip()]
        if items:
            return tuple(items)
    return tuple(DEFAULT_KEYWORDS)


def _load_sources(raw: str | None) -> Tuple[str, ...]:
    if raw:
        items = [item.strip().lower() for item in raw.split(",") if item.strip()]
        if items:
            return tuple(items)
    return DEFAULT_SOURCES


def _load_int_env(name: str, *, default: int, minimum: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}.") from exc
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}, got {value}.")
    return value
