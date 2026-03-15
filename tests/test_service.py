from __future__ import annotations

import json
from datetime import datetime

import pytest

from paper_alert.config import PaperAlertConfig
from paper_alert.models import Paper
from paper_alert.service import collect_new_papers, run_paper_alert
from paper_alert.store import SeenStore, StoreError
from paper_alert.utils import parse_datetime


@pytest.fixture
def cfg(tmp_path) -> PaperAlertConfig:
    return PaperAlertConfig(
        keywords=("temporal interference",),
        sources=("arxiv",),
        max_results=25,
        store_path=tmp_path / "seen.json",
        biorxiv_lookback_days=30,
        semanticscholar_api_key=None,
    )


def test_collect_new_papers_deduplicates_and_persists(monkeypatch, cfg):
    older = Paper(
        source="arxiv",
        identifier="old",
        title="Older paper",
        url="https://example.com/old",
        published=datetime(2023, 6, 1),
    )
    newer = Paper(
        source="arxiv",
        identifier="new",
        title="Newer paper",
        url="https://example.com/new",
        published=datetime(2024, 6, 1),
    )

    def fake_gather(passed_cfg, progress=None):
        assert passed_cfg is cfg
        return [older, newer, older], ["arxiv: transient error"]

    monkeypatch.setattr("paper_alert.service.gather_papers", fake_gather)

    new_papers, errors = collect_new_papers(cfg)

    assert errors == ["arxiv: transient error"]
    assert new_papers == [newer, older]

    store = SeenStore(cfg.store_path)
    assert store.load() == {"arxiv:new", "arxiv:old"}
    assert [paper.identifier for paper in store.query_archive()] == ["new", "old"]

    # Second run should yield no additional papers and leave the store unchanged.
    new_again, errors_again = collect_new_papers(cfg)
    assert new_again == []
    assert errors_again == ["arxiv: transient error"]
    assert store.load() == {"arxiv:new", "arxiv:old"}


def test_collect_new_papers_refuses_corrupt_existing_store(monkeypatch, cfg):
    cfg.store_path.write_text("{not-json", encoding="utf-8")
    paper = Paper(
        source="arxiv",
        identifier="fresh",
        title="Fresh paper",
        url="https://example.com/fresh",
        published=datetime(2024, 7, 1),
    )

    monkeypatch.setattr(
        "paper_alert.service.gather_papers",
        lambda passed_cfg, progress=None: ([paper], []),
    )

    with pytest.raises(StoreError, match="refusing to overwrite"):
        collect_new_papers(cfg)


def test_run_paper_alert_reports_counts(monkeypatch, cfg):
    papers = [
        Paper(
            source="arxiv",
            identifier="old",
            title="Older paper",
            url="https://example.com/old",
            published=datetime(2023, 6, 1),
        ),
        Paper(
            source="arxiv",
            identifier="new",
            title="Newer paper",
            url="https://example.com/new",
            published=datetime(2024, 6, 1),
        ),
        Paper(
            source="arxiv",
            identifier="old",
            title="Older paper",
            url="https://example.com/old",
            published=datetime(2023, 6, 1),
        ),
    ]

    monkeypatch.setattr("paper_alert.service.gather_papers", lambda passed_cfg, progress=None: (papers, []))

    run = run_paper_alert(cfg)

    assert [paper.identifier for paper in run.new_papers] == ["new", "old"]
    assert run.seen_papers == []
    assert [paper.identifier for paper in run.candidate_papers] == ["new", "old"]
    assert run.candidate_count == 2
    assert run.cached_count == 2
    assert run.source_count == 1


def test_run_paper_alert_tracks_seen_candidates(monkeypatch, cfg):
    cfg.store_path.write_text(json.dumps({"seen": ["arxiv:old"]}), encoding="utf-8")
    papers = [
        Paper(
            source="arxiv",
            identifier="old",
            title="Older paper",
            url="https://example.com/old",
            published=datetime(2023, 6, 1),
        ),
        Paper(
            source="arxiv",
            identifier="new",
            title="Newer paper",
            url="https://example.com/new",
            published=datetime(2024, 6, 1),
        ),
    ]

    monkeypatch.setattr("paper_alert.service.gather_papers", lambda passed_cfg, progress=None: (papers, []))

    run = run_paper_alert(cfg)

    assert [paper.identifier for paper in run.new_papers] == ["new"]
    assert [paper.identifier for paper in run.seen_papers] == ["old"]
    assert [paper.identifier for paper in run.candidate_papers] == ["new", "old"]
    assert run.cached_count == 2


def test_run_paper_alert_merges_same_paper_across_sources(monkeypatch, tmp_path):
    cfg = PaperAlertConfig(
        keywords=("temporal interference",),
        sources=("crossref", "semanticscholar"),
        max_results=25,
        store_path=tmp_path / "archive.sqlite3",
        biorxiv_lookback_days=30,
        semanticscholar_api_key=None,
    )
    papers = [
        Paper(
            source="crossref",
            identifier="10.1000/example",
            title="Merged paper",
            url="https://doi.org/10.1000/example",
            published=datetime(2024, 6, 1),
            doi="10.1000/example",
        ),
        Paper(
            source="semanticscholar",
            identifier="semantic-id",
            title="Merged paper",
            url="https://www.semanticscholar.org/paper/example",
            published=datetime(2024, 6, 2),
            doi="10.1000/example",
        ),
    ]

    monkeypatch.setattr("paper_alert.service.gather_papers", lambda passed_cfg, progress=None: (papers, []))

    run = run_paper_alert(cfg)

    assert len(run.candidate_papers) == 1
    assert run.candidate_papers[0].canonical_id == "doi:10.1000/example"
    assert run.candidate_papers[0].all_sources == ("crossref", "semanticscholar")


def test_run_paper_alert_handles_mixed_datetime_formats(monkeypatch, cfg):
    papers = [
        Paper(
            source="arxiv",
            identifier="offset",
            title="Offset paper",
            url="https://example.com/offset",
            published=parse_datetime("2024-06-02T00:30:00+00:00"),
        ),
        Paper(
            source="arxiv",
            identifier="naive",
            title="Naive paper",
            url="https://example.com/naive",
            published=datetime(2024, 6, 1),
        ),
    ]

    monkeypatch.setattr(
        "paper_alert.service.gather_papers",
        lambda passed_cfg, progress=None: (papers, []),
    )

    run = run_paper_alert(cfg)

    assert [paper.identifier for paper in run.new_papers] == ["offset", "naive"]
    assert all(paper.published is None or paper.published.tzinfo is None for paper in run.new_papers)
