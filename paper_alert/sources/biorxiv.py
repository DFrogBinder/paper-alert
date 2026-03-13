from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable, List

from ..constants import BIORXIV_LOOKBACK, MAX_RESULTS_PER_SOURCE
from ..http import fetch_json
from ..models import Paper
from ..utils import clean_title, matches_keywords, parse_datetime

BASE_URL = "https://api.biorxiv.org/details/{server}/{start}/{end}/0"


def _date_range(lookback: timedelta) -> tuple[str, str]:
    today = datetime.utcnow().date()
    start = today - lookback
    return start.isoformat(), today.isoformat()


def _convert_item(server: str, item: dict, keywords: Iterable[str]) -> Paper | None:
    title = clean_title(item.get("title"))
    text = title + " " + (item.get("abstract", "") or "")
    if not matches_keywords(text, keywords):
        return None
    doi = item.get("doi") or item.get("biorxiv_doi")
    identifier = doi or item.get("pwi") or title
    published = (
        parse_datetime(item.get("date"))
        or parse_datetime(item.get("rel_date"))
        or parse_datetime(item.get("published"))
    )
    url = f"https://doi.org/{doi}" if doi else item.get("rel_link") or ""
    return Paper(
        source=server,
        identifier=str(identifier),
        title=title,
        url=url or "https://www.biorxiv.org/",  # fallback to portal
        published=published,
    )


def _fetch_server(server: str, keywords: Iterable[str], *, lookback: timedelta, max_results: int) -> List[Paper]:
    start, end = _date_range(lookback)
    url = BASE_URL.format(server=server, start=start, end=end)
    data = fetch_json(url)
    collection = data.get("collection", [])
    papers: List[Paper] = []
    for item in collection:
        paper = _convert_item(server, item, keywords)
        if not paper:
            continue
        papers.append(paper)
        if len(papers) >= max_results:
            break
    return papers


def fetch_biorxiv(
    keywords: Iterable[str],
    max_results: int = MAX_RESULTS_PER_SOURCE,
    lookback: timedelta = BIORXIV_LOOKBACK,
) -> List[Paper]:
    return _fetch_server("biorxiv", keywords, lookback=lookback, max_results=max_results)


def fetch_medrxiv(
    keywords: Iterable[str],
    max_results: int = MAX_RESULTS_PER_SOURCE,
    lookback: timedelta = BIORXIV_LOOKBACK,
) -> List[Paper]:
    return _fetch_server("medrxiv", keywords, lookback=lookback, max_results=max_results)
