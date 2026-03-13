from __future__ import annotations

import pytest

from paper_alert import cli


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
