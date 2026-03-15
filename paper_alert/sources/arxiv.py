from __future__ import annotations

from datetime import datetime
from typing import Iterable, List
from urllib.parse import quote_plus
from xml.etree import ElementTree as ET

from ..constants import MAX_RESULTS_PER_SOURCE
from ..http import fetch_text
from ..models import Paper
from ..utils import clean_title, matches_keywords, parse_datetime

ATOM_NS = "http://www.w3.org/2005/Atom"
NS = {"atom": ATOM_NS}


def build_query(keywords: Iterable[str]) -> str:
    clauses = [f"all:\"{kw}\"" for kw in keywords]
    return quote_plus(" OR ".join(clauses))


def fetch_arxiv(keywords: Iterable[str], max_results: int = MAX_RESULTS_PER_SOURCE) -> List[Paper]:
    query = build_query(keywords)
    url = (
        "http://export.arxiv.org/api/query?"
        f"search_query={query}&sortBy=submittedDate&sortOrder=descending&max_results={max_results}"
    )
    payload = fetch_text(url)
    root = ET.fromstring(payload)
    papers: List[Paper] = []
    for entry in root.findall("atom:entry", NS):
        identifier = entry.findtext(f"{{{ATOM_NS}}}id", default="").strip()
        title = clean_title(entry.findtext(f"{{{ATOM_NS}}}title", default=""))
        summary = clean_title(entry.findtext(f"{{{ATOM_NS}}}summary", default=""))
        if not matches_keywords(f"{title} {summary}", keywords):
            continue
        published_raw = entry.findtext(f"{{{ATOM_NS}}}published", default="")
        updated_raw = entry.findtext(f"{{{ATOM_NS}}}updated", default="")
        published = parse_datetime(published_raw) or parse_datetime(updated_raw)
        link = identifier
        for link_el in entry.findall(f"{{{ATOM_NS}}}link"):
            rel = link_el.attrib.get("rel")
            if rel == "alternate":
                link = link_el.attrib.get("href", link)
                break
        papers.append(
            Paper(
                source="arxiv",
                identifier=identifier,
                title=title,
                url=link,
                published=published,
                arxiv_id=identifier or link,
            )
        )
    return papers
