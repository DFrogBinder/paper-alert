from __future__ import annotations

import threading
from datetime import datetime

from paper_alert import aggregator
from paper_alert.config import PaperAlertConfig
from paper_alert.http import FetchError
from paper_alert.models import Paper


def _make_cfg(tmp_path, sources: tuple[str, ...]) -> PaperAlertConfig:
    return PaperAlertConfig(
        keywords=("temporal interference",),
        sources=sources,
        max_results=25,
        store_path=tmp_path / "seen.json",
        biorxiv_lookback_days=30,
        semanticscholar_api_key=None,
    )


def _make_paper(source: str, identifier: str) -> Paper:
    return Paper(
        source=source,
        identifier=identifier,
        title=f"{source} paper",
        url=f"https://example.com/{identifier}",
        published=datetime(2024, 6, 1),
    )


def test_gather_papers_fetches_sources_in_parallel(monkeypatch, tmp_path):
    cfg = _make_cfg(tmp_path, ("one", "two"))
    first_started = threading.Event()
    second_started = threading.Event()
    release = threading.Event()
    result: dict[str, tuple[list[Paper], list[str]]] = {}
    failures: list[Exception] = []

    def build_fetcher(source: str, started: threading.Event):
        def fetch(_cfg: PaperAlertConfig) -> list[Paper]:
            started.set()
            assert release.wait(timeout=1), "parallel fetch did not start in time"
            return [_make_paper(source, source)]

        return fetch

    monkeypatch.setattr(
        aggregator,
        "FETCHERS",
        {
            "one": build_fetcher("one", first_started),
            "two": build_fetcher("two", second_started),
        },
    )

    def run() -> None:
        try:
            result["value"] = aggregator.gather_papers(cfg)
        except Exception as exc:  # pragma: no cover - defensive test harness
            failures.append(exc)

    runner = threading.Thread(target=run)
    runner.start()

    assert first_started.wait(timeout=0.5)
    assert second_started.wait(timeout=0.5)

    release.set()
    runner.join(timeout=1)

    assert not runner.is_alive()
    assert failures == []
    papers, errors = result["value"]
    assert errors == []
    assert {paper.source for paper in papers} == {"one", "two"}


def test_gather_papers_collects_parallel_results_errors_and_progress(monkeypatch, tmp_path):
    cfg = _make_cfg(tmp_path, ("one", "unknown", "two"))
    progress_messages: list[str] = []

    def fetch_ok(_cfg: PaperAlertConfig) -> list[Paper]:
        return [_make_paper("one", "ok")]

    def fetch_error(_cfg: PaperAlertConfig) -> list[Paper]:
        raise FetchError("boom")

    monkeypatch.setattr(
        aggregator,
        "FETCHERS",
        {
            "one": fetch_ok,
            "two": fetch_error,
        },
    )

    papers, errors = aggregator.gather_papers(cfg, progress=progress_messages.append)

    assert [paper.identifier for paper in papers] == ["ok"]
    assert "unknown source 'unknown' - skipping" in errors
    assert "two: boom" in errors
    assert "checking one" in progress_messages
    assert "checking unknown" in progress_messages
    assert "checking two" in progress_messages
    assert "unknown: skipped (unknown source)" in progress_messages
    assert "one: 1 candidate papers" in progress_messages
    assert "two: request failed" in progress_messages
