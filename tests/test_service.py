from __future__ import annotations

import json
from datetime import datetime

import pytest

from paper_alert.config import PaperAlertConfig
from paper_alert.models import Paper
from paper_alert.service import collect_new_papers, run_paper_alert


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

    payload = json.loads(cfg.store_path.read_text(encoding="utf-8"))
    assert payload["seen"] == ["arxiv:new", "arxiv:old"]

    # Second run should yield no additional papers and leave the store unchanged.
    new_again, errors_again = collect_new_papers(cfg)
    assert new_again == []
    assert errors_again == ["arxiv: transient error"]
    payload = json.loads(cfg.store_path.read_text(encoding="utf-8"))
    assert payload["seen"] == ["arxiv:new", "arxiv:old"]


def test_collect_new_papers_surfaces_corrupt_store_warning(monkeypatch, cfg):
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

    new_papers, errors = collect_new_papers(cfg)

    assert new_papers == [paper]
    assert errors == [
        f"store: seen-store at {cfg.store_path} contains invalid JSON; treating it as empty"
    ]
    payload = json.loads(cfg.store_path.read_text(encoding="utf-8"))
    assert payload["seen"] == ["arxiv:fresh"]


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
    assert run.candidate_count == 2
    assert run.cached_count == 2
    assert run.source_count == 1
