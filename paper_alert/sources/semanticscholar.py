from __future__ import annotations

from typing import Iterable, List
from urllib.parse import urlencode

from ..constants import MAX_RESULTS_PER_SOURCE
from ..http import fetch_json
from ..models import Paper
from ..utils import clean_title, matches_keywords, parse_datetime

BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"


def fetch_semantic_scholar(
    keywords: Iterable[str],
    max_results: int = MAX_RESULTS_PER_SOURCE,
    api_key: str | None = None,
) -> List[Paper]:
    query = " OR ".join(f'"{kw}"' for kw in keywords)
    params = {
        "query": query,
        "limit": max_results,
        "fields": "paperId,title,abstract,url,publicationDate,externalIds",
    }
    url = f"{BASE_URL}?{urlencode(params)}"
    headers = {"x-api-key": api_key} if api_key else None
    payload = fetch_json(url, headers=headers)
    papers: List[Paper] = []
    for item in payload.get("data", []):
        title = clean_title(item.get("title"))
        abstract = item.get("abstract") or ""
        if not matches_keywords(f"{title} {abstract}", keywords):
            continue
        external_ids = item.get("externalIds")
        if not isinstance(external_ids, dict):
            external_ids = {}
        identifier = (
            item.get("paperId")
            or external_ids.get("DOI")
            or external_ids.get("ArXiv")
            or title
        )
        published = parse_datetime(item.get("publicationDate"))
        link = item.get("url")
        if not link and identifier:
            link = f"https://www.semanticscholar.org/paper/{identifier}"
        papers.append(
            Paper(
                source="semanticscholar",
                identifier=str(identifier),
                title=title,
                url=link or "https://www.semanticscholar.org/",
                published=published,
            )
        )
    return papers
