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
    store_path = tmp_path / "archive.sqlite3"
    store = SeenStore(store_path)

    first = _make_paper("id-1", datetime(2024, 1, 5))
    second = _make_paper("id-2", datetime(2024, 1, 10))

    new_papers = store.mark_seen([first, second])
    assert new_papers == [first, second]
    assert store.load() == {"arxiv:id-1", "arxiv:id-2"}
    assert [paper.identifier for paper in store.query_archive()] == ["id-2", "id-1"]

    third = _make_paper("id-3", datetime(2024, 2, 2))
    new_again = store.mark_seen([second, third])
    assert new_again == [third]

    assert store.load() == {"arxiv:id-1", "arxiv:id-2", "arxiv:id-3"}


def test_query_archive_filters_by_state_and_search(tmp_path):
    store = SeenStore(tmp_path / "archive.sqlite3")
    first = _make_paper("id-1", datetime(2024, 1, 5))
    second = Paper(
        source="crossref",
        identifier="10.1000/example",
        title="Merged field shaping paper",
        url="https://doi.org/10.1000/example",
        published=datetime(2024, 2, 1),
        doi="10.1000/example",
    )

    store.mark_seen([first, second])
    assert store.set_triage_state("doi:10.1000/example", "saved")

    saved = store.query_archive(triage_state="saved")
    assert [paper.canonical_id for paper in saved] == ["doi:10.1000/example"]

    searched = store.query_archive(search="field shaping")
    assert [paper.title for paper in searched] == ["Merged field shaping paper"]


def test_store_migrates_legacy_json(tmp_path):
    store_path = tmp_path / "seen.json"
    store_path.write_text(json.dumps({"seen": ["arxiv:old"]}), encoding="utf-8")

    store = SeenStore(store_path)

    assert store.load() == {"arxiv:old"}
    assert any("migrated legacy seen-store" in warning for warning in store.warnings)
