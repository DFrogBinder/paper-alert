from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Iterable, List, Tuple

from .aggregator import gather_papers
from .config import PaperAlertConfig
from .models import Paper
from .store import SeenStore


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


def run_paper_alert(
    cfg: PaperAlertConfig,
    *,
    progress: Callable[[str], None] | None = None,
) -> PaperAlertRun:
    papers, errors = gather_papers(cfg, progress=progress)
    candidate_papers = _sort_papers(_deduplicate(papers))
    store = SeenStore(cfg.store_path)
    new_papers = store.mark_seen(candidate_papers)
    errors.extend(store.warnings)
    cached_count = len(store.load())
    return PaperAlertRun(
        new_papers=new_papers,
        errors=errors,
        cached_count=cached_count,
        candidate_count=len(candidate_papers),
        source_count=len(cfg.sources),
        candidate_papers=candidate_papers,
    )


def collect_new_papers(cfg: PaperAlertConfig) -> Tuple[List[Paper], List[str]]:
    run = run_paper_alert(cfg)
    return run.new_papers, run.errors
