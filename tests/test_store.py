from __future__ import annotations

import json
from datetime import datetime

from paper_alert.models import Paper
from paper_alert.store import SeenStore


def _make_paper(identifier: str, published: datetime) -> Paper:
    return Paper(
        source="arxiv",
        identifier=identifier,
        title=f"Paper {identifier}",
        url=f"https://example.com/{identifier}",
        published=published,
    )


def test_mark_seen_persists_new_entries(tmp_path):
    store_path = tmp_path / "seen.json"
    store = SeenStore(store_path)

    first = _make_paper("id-1", datetime(2024, 1, 5))
    second = _make_paper("id-2", datetime(2024, 1, 10))

    new_papers = store.mark_seen([first, second])
    assert new_papers == [first, second]

    payload = json.loads(store_path.read_text(encoding="utf-8"))
    assert payload["seen"] == ["arxiv:id-1", "arxiv:id-2"]

    third = _make_paper("id-3", datetime(2024, 2, 2))
    new_again = store.mark_seen([second, third])
    assert new_again == [third]

    payload = json.loads(store_path.read_text(encoding="utf-8"))
    assert payload["seen"] == ["arxiv:id-1", "arxiv:id-2", "arxiv:id-3"]
