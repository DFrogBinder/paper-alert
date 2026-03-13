from __future__ import annotations

from typing import Iterable, List
from urllib.parse import quote_plus

from ..constants import MAX_RESULTS_PER_SOURCE
from ..http import fetch_json
from ..models import Paper
from ..utils import clean_title, matches_keywords, parse_date_parts

CROSSREF_URL = "https://api.crossref.org/works?query={query}&rows={rows}&sort=deposited&order=desc"


def fetch_crossref(keywords: Iterable[str], max_results: int = MAX_RESULTS_PER_SOURCE) -> List[Paper]:
    query = quote_plus(" OR ".join(f'"{kw}"' for kw in keywords))
    url = CROSSREF_URL.format(query=query, rows=max_results)
    payload = fetch_json(url)
    items = payload.get("message", {}).get("items", [])
    papers: List[Paper] = []
    for item in items:
        title_list = item.get("title") or []
        if not title_list:
            continue
        title = clean_title(title_list[0])
        abstract = item.get("abstract") or ""
        if not matches_keywords(f"{title} {abstract}", keywords):
            continue
        doi = item.get("DOI") or item.get("doi")
        identifier = doi or item.get("URL") or title
        published = (
            parse_date_parts(item.get("issued", {}).get("date-parts"))
            or parse_date_parts(item.get("published", {}).get("date-parts"))
        )
        url = item.get("URL") or (f"https://doi.org/{doi}" if doi else "")
        papers.append(
            Paper(
                source="crossref",
                identifier=str(identifier),
                title=title,
                url=url or "https://search.crossref.org/",
                published=published,
            )
        )
    return papers
