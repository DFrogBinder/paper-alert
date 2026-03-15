from __future__ import annotations

from paper_alert.utils import parse_datetime


def test_parse_datetime_normalizes_offset_datetimes_to_naive_utc():
    parsed = parse_datetime("2024-06-02T00:30:00+00:00")

    assert parsed is not None
    assert parsed.isoformat() == "2024-06-02T00:30:00"
    assert parsed.tzinfo is None
