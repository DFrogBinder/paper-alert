from __future__ import annotations

from datetime import datetime

from paper_alert.models import Paper
from paper_alert.service import PaperAlertRun


def test_main_always_shows_store_warnings(monkeypatch, capsys, tmp_path):
    cfg_path = tmp_path / "seen.json"
    cfg_path.write_text("{broken", encoding="utf-8")

    monkeypatch.setenv("PAPER_ALERT_STORE", str(cfg_path))
    monkeypatch.setattr(
        "paper_alert.service.gather_papers",
        lambda passed_cfg, progress=None: ([], []),
    )

    from paper_alert import cli

    exit_code = cli.main(["--quiet-if-none"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Warnings" in captured.out
    assert "store: seen-store at" in captured.out


def test_main_renders_summary_banner_by_default_and_hides_optional_errors(monkeypatch, capsys):
    paper = Paper(
        source="arxiv",
        identifier="one",
        title="Useful paper",
        url="https://example.com/one",
        published=datetime(2024, 6, 1),
    )

    monkeypatch.setattr(
        "paper_alert.cli.run_paper_alert",
        lambda cfg, progress=None: PaperAlertRun(
            new_papers=[paper],
            errors=["arxiv: transient error"],
            cached_count=1,
            candidate_count=1,
            source_count=1,
            candidate_papers=[paper],
        ),
    )

    from paper_alert import cli

    exit_code = cli.main([])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Paper Alert" in captured.out
    assert "1 new paper ready to review" in captured.out
    assert "Useful paper" not in captured.out
    assert "transient error" not in captured.out


def test_main_prints_summary_when_requested(monkeypatch, capsys):
    monkeypatch.setattr(
        "paper_alert.cli.run_paper_alert",
        lambda cfg, progress=None: PaperAlertRun(
            new_papers=[],
            errors=[],
            cached_count=14,
            candidate_count=3,
            source_count=6,
        ),
    )

    from paper_alert import cli

    exit_code = cli.main(["--show-summary"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "paper-alert: 6 sources checked, 3 candidate papers, 0 new, 14 cached" in captured.out


def test_main_prints_progress_when_requested(monkeypatch, capsys):
    def fake_run(cfg, progress=None):
        assert progress is not None
        progress("checking arxiv")
        return PaperAlertRun(
            new_papers=[],
            errors=[],
            cached_count=2,
            candidate_count=1,
            source_count=1,
        )

    monkeypatch.setattr("paper_alert.cli.run_paper_alert", fake_run)

    from paper_alert import cli

    exit_code = cli.main(["--show-summary", "--show-progress"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "[paper-alert] checking arxiv" in captured.out


def test_main_prints_new_papers_when_requested(monkeypatch, capsys):
    paper = Paper(
        source="arxiv",
        identifier="one",
        title="Useful paper",
        url="https://example.com/one",
        published=datetime(2024, 6, 1),
    )

    monkeypatch.setattr(
        "paper_alert.cli.run_paper_alert",
        lambda cfg, progress=None: PaperAlertRun(
            new_papers=[paper],
            errors=[],
            cached_count=1,
            candidate_count=1,
            source_count=1,
            candidate_papers=[paper],
        ),
    )

    from paper_alert import cli

    exit_code = cli.main(["--show-new"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "New Papers" in captured.out
    assert "Useful paper" in captured.out


def test_main_prints_candidates_when_requested(monkeypatch, capsys):
    candidates = [
        Paper(
            source="arxiv",
            identifier="one",
            title="Candidate paper one",
            url="https://example.com/one",
            published=datetime(2024, 6, 1),
        ),
        Paper(
            source="pubmed",
            identifier="two",
            title="Candidate paper two",
            url="https://example.com/two",
            published=datetime(2024, 5, 1),
        ),
    ]

    monkeypatch.setattr(
        "paper_alert.cli.run_paper_alert",
        lambda cfg, progress=None: PaperAlertRun(
            new_papers=[],
            errors=[],
            cached_count=14,
            candidate_count=2,
            source_count=6,
            candidate_papers=candidates,
        ),
    )

    from paper_alert import cli

    exit_code = cli.main(["--show-candidate"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Candidate Papers" in captured.out
    assert "Candidate paper one" in captured.out
    assert "Candidate paper two" in captured.out
    assert "No new temporal interference papers detected." not in captured.out
