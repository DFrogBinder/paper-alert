from __future__ import annotations

from typing import Callable, Dict, List, Tuple

from .config import PaperAlertConfig
from .http import FetchError
from .models import Paper
from .sources import (
    fetch_arxiv,
    fetch_biorxiv,
    fetch_crossref,
    fetch_medrxiv,
    fetch_pubmed,
    fetch_semantic_scholar,
)

Fetcher = Callable[[PaperAlertConfig], List[Paper]]
ProgressCallback = Callable[[str], None]


def _build_fetchers() -> Dict[str, Fetcher]:
    return {
        "arxiv": lambda cfg: fetch_arxiv(cfg.keywords, cfg.max_results),
        "pubmed": lambda cfg: fetch_pubmed(cfg.keywords, cfg.max_results),
        "biorxiv": lambda cfg: fetch_biorxiv(
            cfg.keywords, cfg.max_results, lookback=cfg.biorxiv_lookback
        ),
        "medrxiv": lambda cfg: fetch_medrxiv(
            cfg.keywords, cfg.max_results, lookback=cfg.biorxiv_lookback
        ),
        "crossref": lambda cfg: fetch_crossref(cfg.keywords, cfg.max_results),
        "semanticscholar": lambda cfg: fetch_semantic_scholar(
            cfg.keywords, cfg.max_results, api_key=cfg.semanticscholar_api_key
        ),
    }


FETCHERS = _build_fetchers()


def gather_papers(
    cfg: PaperAlertConfig,
    *,
    progress: ProgressCallback | None = None,
) -> Tuple[List[Paper], List[str]]:
    papers: List[Paper] = []
    errors: List[str] = []
    for source in cfg.sources:
        if progress:
            progress(f"checking {source}")
        fetcher = FETCHERS.get(source)
        if not fetcher:
            errors.append(f"unknown source '{source}' - skipping")
            if progress:
                progress(f"{source}: skipped (unknown source)")
            continue
        try:
            fetched = fetcher(cfg)
            papers.extend(fetched)
            if progress:
                progress(f"{source}: {len(fetched)} candidate papers")
        except FetchError as exc:
            errors.append(f"{source}: {exc}")
            if progress:
                progress(f"{source}: request failed")
        except Exception as exc:  # pragma: no cover - defensive fallback
            errors.append(f"{source}: unexpected error {exc}")
            if progress:
                progress(f"{source}: unexpected failure")
    return papers, errors
