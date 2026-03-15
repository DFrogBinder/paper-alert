from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
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
MAX_CONCURRENT_FETCHES = 4


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


def _fetch_source(
    source: str,
    fetcher: Fetcher,
    cfg: PaperAlertConfig,
) -> tuple[str, List[Paper], str | None, str | None]:
    try:
        return source, fetcher(cfg), None, None
    except FetchError as exc:
        return source, [], f"{source}: {exc}", "request failed"
    except Exception as exc:  # pragma: no cover - defensive fallback
        return source, [], f"{source}: unexpected error {exc}", "unexpected failure"


def gather_papers(
    cfg: PaperAlertConfig,
    *,
    progress: ProgressCallback | None = None,
) -> Tuple[List[Paper], List[str]]:
    papers: List[Paper] = []
    errors: List[str] = []
    scheduled_fetches: list[tuple[str, Fetcher]] = []
    for source in cfg.sources:
        if progress:
            progress(f"checking {source}")
        fetcher = FETCHERS.get(source)
        if not fetcher:
            errors.append(f"unknown source '{source}' - skipping")
            if progress:
                progress(f"{source}: skipped (unknown source)")
            continue
        scheduled_fetches.append((source, fetcher))

    if not scheduled_fetches:
        return papers, errors

    max_workers = min(len(scheduled_fetches), MAX_CONCURRENT_FETCHES)
    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="paper-alert") as executor:
        future_map = {
            executor.submit(_fetch_source, source, fetcher, cfg): source
            for source, fetcher in scheduled_fetches
        }
        for future in as_completed(future_map):
            source, fetched, error, failure_progress = future.result()
            if error is not None:
                errors.append(error)
                if progress:
                    progress(f"{source}: {failure_progress}")
                continue
            papers.extend(fetched)
            if progress:
                progress(f"{source}: {len(fetched)} candidate papers")
    return papers, errors
