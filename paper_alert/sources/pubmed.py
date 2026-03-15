from __future__ import annotations

from typing import Iterable, List
from urllib.parse import quote_plus

from ..constants import MAX_RESULTS_PER_SOURCE
from ..http import fetch_json, polite_delay
from ..models import Paper
from ..utils import clean_title, parse_datetime, parse_pubmed_sortdate

PUBMED_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"


def build_term(keywords: Iterable[str]) -> str:
    return " OR ".join(f'"{kw}"' for kw in keywords)


def fetch_pubmed(keywords: Iterable[str], max_results: int = MAX_RESULTS_PER_SOURCE) -> List[Paper]:
    term = quote_plus(build_term(keywords))
    esearch_url = (
        f"{PUBMED_ESEARCH}?db=pubmed&retmode=json&retmax={max_results}&sort=pub+date&term={term}"
    )
    search = fetch_json(esearch_url)
    idlist = search.get("esearchresult", {}).get("idlist", [])
    if not idlist:
        return []
    polite_delay()
    esummary_url = (
        f"{PUBMED_ESUMMARY}?db=pubmed&retmode=json&id={','.join(idlist)}"
    )
    summary = fetch_json(esummary_url)
    result = summary.get("result", {})
    uids = result.get("uids", [])
    papers: List[Paper] = []
    for uid in uids:
        payload = result.get(uid, {})
        title = clean_title(payload.get("title"))
        sort_date = parse_pubmed_sortdate(payload.get("sortpubdate"))
        published = sort_date or parse_datetime(payload.get("pubdate"))
        link = f"https://pubmed.ncbi.nlm.nih.gov/{uid}/"
        doi = None
        for article_id in payload.get("articleids", []) or []:
            if not isinstance(article_id, dict):
                continue
            if str(article_id.get("idtype", "")).lower() == "doi":
                doi = article_id.get("value")
                break
        papers.append(
            Paper(
                source="pubmed",
                identifier=str(uid),
                title=title,
                url=link,
                published=published,
                doi=doi,
                pmid=str(uid),
            )
        )
    return papers
