from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Callable, Iterable, List, Tuple

from .constants import DEFAULT_TRIAGE_STATE
from .aggregator import gather_papers
from .config import PaperAlertConfig
from .models import Paper
from .store import SeenStore

SOURCE_PRIORITY = (
    "pubmed",
    "crossref",
    "arxiv",
    "biorxiv",
    "medrxiv",
    "semanticscholar",
)


def _source_rank(source: str) -> tuple[int, str]:
    lowered = source.lower()
    try:
        return SOURCE_PRIORITY.index(lowered), lowered
    except ValueError:
        return len(SOURCE_PRIORITY), lowered


def _deduplicate(papers: Iterable[Paper]) -> List[Paper]:
    seen: set[str] = set()
    unique: List[Paper] = []
    for paper in papers:
        key = paper.key
        if key in seen:
            continue
        seen.add(key)
        unique.append(paper)
    return unique


def _merge_group(papers: list[Paper]) -> Paper:
    if len(papers) == 1:
        return papers[0]
    if all(paper == papers[0] for paper in papers[1:]):
        return papers[0]

    primary = min(
        papers,
        key=lambda paper: (_source_rank(paper.source), 0 if paper.url else 1, paper.title),
    )
    published_values = [paper.published for paper in papers if paper.published is not None]
    published = max(published_values) if published_values else None
    sources = _unique_in_order(
        paper.source
        for paper in sorted(papers, key=lambda paper: _source_rank(paper.source))
    )
    urls = _unique_in_order(url for paper in papers for url in paper.all_urls)
    primary_url = primary.url or (urls[0] if urls else "")
    return Paper(
        source=primary.source,
        identifier=primary.identifier,
        title=max(papers, key=lambda paper: (paper.title != "Untitled", len(paper.title))).title,
        url=primary_url,
        published=published,
        doi=next((paper.doi for paper in papers if paper.doi), None),
        arxiv_id=next((paper.arxiv_id for paper in papers if paper.arxiv_id), None),
        pmid=next((paper.pmid for paper in papers if paper.pmid), None),
        triage_state=primary.triage_state,
        sources=tuple(sources),
        alternate_urls=tuple(url for url in urls if url and url != primary_url),
        canonical_id_override=primary.canonical_id,
    )


def _merge_papers(papers: Iterable[Paper]) -> List[Paper]:
    grouped: dict[str, list[Paper]] = {}
    for paper in papers:
        grouped.setdefault(paper.key, []).append(paper)
    return [_merge_group(group) for group in grouped.values()]


def _sort_papers(papers: Iterable[Paper]) -> List[Paper]:
    return sorted(papers, key=lambda p: p.published or datetime.min, reverse=True)


@dataclass(slots=True)
class PaperAlertRun:
    new_papers: List[Paper]
    errors: List[str]
    cached_count: int
    candidate_count: int
    source_count: int
    candidate_papers: List[Paper] = field(default_factory=list)
    seen_papers: List[Paper] = field(default_factory=list)


def run_paper_alert(
    cfg: PaperAlertConfig,
    *,
    progress: Callable[[str], None] | None = None,
) -> PaperAlertRun:
    papers, errors = gather_papers(cfg, progress=progress)
    candidate_papers = _sort_papers(_deduplicate(_merge_papers(papers)))
    store = SeenStore(cfg.store_path)
    stored_papers = store.load_papers(paper.key for paper in candidate_papers)
    annotated_candidates: List[Paper] = []
    new_papers: List[Paper] = []
    seen_papers: List[Paper] = []
    for paper in candidate_papers:
        archived = stored_papers.get(paper.key)
        if archived is not None:
            annotated = replace(paper, triage_state=archived.triage_state)
            annotated_candidates.append(annotated)
            seen_papers.append(annotated)
            continue
        annotated = replace(paper, triage_state=DEFAULT_TRIAGE_STATE)
        annotated_candidates.append(annotated)
        new_papers.append(annotated)
    store.upsert_papers(annotated_candidates)
    cached_count = store.count()
    errors.extend(store.warnings)
    return PaperAlertRun(
        new_papers=new_papers,
        errors=errors,
        cached_count=cached_count,
        candidate_count=len(annotated_candidates),
        source_count=len(cfg.sources),
        candidate_papers=annotated_candidates,
        seen_papers=seen_papers,
    )


def collect_new_papers(cfg: PaperAlertConfig) -> Tuple[List[Paper], List[str]]:
    run = run_paper_alert(cfg)
    return run.new_papers, run.errors


def _unique_in_order(values: Iterable[str]) -> list[str]:
    unique: list[str] = []
    for value in values:
        if not value or value in unique:
            continue
        unique.append(value)
    return unique
