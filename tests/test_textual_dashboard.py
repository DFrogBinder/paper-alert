from __future__ import annotations

import asyncio
from datetime import datetime

from textual.widgets import Static

from paper_alert.models import Paper
from paper_alert.service import PaperAlertRun
from paper_alert.textual_dashboard import PaperAlertDashboard


def _static_text(widget: Static) -> str:
    content = getattr(widget, "renderable", None)
    if content is None:
        content = getattr(widget, "_content", None)
    if content is None:
        content = widget.render()
    return str(content)


def _build_run(
    candidate_papers: list[Paper],
    *,
    new_papers: list[Paper] | None = None,
    seen_papers: list[Paper] | None = None,
) -> PaperAlertRun:
    new_list = list(new_papers or [])
    seen_list = list(seen_papers or [])
    return PaperAlertRun(
        new_papers=new_list,
        errors=[],
        cached_count=0,
        candidate_count=len(candidate_papers),
        source_count=1,
        candidate_papers=list(candidate_papers),
        seen_papers=seen_list,
    )


def test_dashboard_opens_selected_paper_in_browser():
    paper = Paper(
        source="arxiv",
        identifier="one",
        title="Professional dashboard paper",
        url="https://example.com/one",
        published=datetime(2024, 6, 1),
    )
    opened: list[str] = []

    def fake_open(url: str) -> bool:
        opened.append(url)
        return True

    async def exercise() -> None:
        app = PaperAlertDashboard(_build_run([paper], new_papers=[paper]), open_url=fake_open)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")

    asyncio.run(exercise())

    assert opened == [paper.url]


def test_dashboard_updates_selection_status_when_highlight_changes():
    first = Paper(
        source="arxiv",
        identifier="one",
        title="First paper",
        url="https://example.com/one",
        published=datetime(2024, 6, 1),
    )
    second = Paper(
        source="pubmed",
        identifier="two",
        title="Second paper",
        url="https://example.com/two",
        published=datetime(2024, 6, 2),
    )

    async def exercise() -> None:
        app = PaperAlertDashboard(_build_run([first, second], new_papers=[first, second]))
        async with app.run_test() as pilot:
            await pilot.pause()
            status = app.query_one("#selection-status", Static)
            assert first.title in _static_text(status)
            await pilot.press("down")
            status = app.query_one("#selection-status", Static)
            assert second.title in _static_text(status)

    asyncio.run(exercise())


def test_dashboard_can_browse_seen_papers():
    new_paper = Paper(
        source="arxiv",
        identifier="one",
        title="New paper",
        url="https://example.com/one",
        published=datetime(2024, 6, 2),
    )
    seen_paper = Paper(
        source="pubmed",
        identifier="two",
        title="Seen paper",
        url="https://example.com/two",
        published=datetime(2024, 6, 1),
    )

    async def exercise() -> None:
        app = PaperAlertDashboard(
            _build_run(
                [new_paper, seen_paper],
                new_papers=[new_paper],
                seen_papers=[seen_paper],
            )
        )
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("s")
            status = app.query_one("#selection-status", Static)
            assert seen_paper.title in _static_text(status)
            assert "Status: SEEN" in _static_text(status)

    asyncio.run(exercise())
