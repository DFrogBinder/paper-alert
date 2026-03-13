from __future__ import annotations

from paper_alert.http import fetch_bytes


class _FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return b"payload"


def test_fetch_bytes_reads_user_agent_at_call_time(monkeypatch):
    captured: dict[str, str] = {}

    def fake_urlopen(request, timeout):
        captured.update(dict(request.header_items()))
        return _FakeResponse()

    monkeypatch.setattr("paper_alert.http.urlopen", fake_urlopen)
    monkeypatch.setenv("PAPER_ALERT_USER_AGENT", "PaperAlert/Test")

    payload = fetch_bytes("https://example.com/papers")

    assert payload == b"payload"
    assert captured["User-agent"] == "PaperAlert/Test"
