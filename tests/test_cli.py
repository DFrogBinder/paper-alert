from __future__ import annotations

import pytest

from paper_alert import cli
from paper_alert.service import PaperAlertRun


def test_main_rejects_non_positive_max_results(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--max-results", "0"])

    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "greater than or equal to 1" in captured.err


def test_main_rejects_invalid_env_max_results(monkeypatch, capsys):
    monkeypatch.setenv("PAPER_ALERT_MAX_RESULTS", "not-an-int")

    with pytest.raises(SystemExit) as exc:
        cli.main([])

    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "PAPER_ALERT_MAX_RESULTS must be an integer" in captured.err


def test_main_rejects_unknown_sources(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--sources", "arxiv,unknown"])

    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "unknown source" in captured.err


def test_main_normalizes_and_deduplicates_sources_override(monkeypatch):
    captured_sources: dict[str, tuple[str, ...]] = {}

    def fake_run(cfg, progress=None):
        captured_sources["value"] = cfg.sources
        return PaperAlertRun(
            new_papers=[],
            errors=[],
            cached_count=0,
            candidate_count=0,
            source_count=len(cfg.sources),
        )

    monkeypatch.setattr("paper_alert.cli.run_paper_alert", fake_run)

    exit_code = cli.main(["--quiet-if-none", "--sources", "arxiv,ARXIV,pubmed"])

    assert exit_code == 0
    assert captured_sources["value"] == ("arxiv", "pubmed")
