from __future__ import annotations

import asyncio
from datetime import datetime

from textual.widgets import Static

from paper_alert.models import Paper
from paper_alert.service import PaperAlertRun
from paper_alert.textual_dashboard import PaperAlertDashboard


def _build_run(*papers: Paper) -> PaperAlertRun:
    paper_list = list(papers)
    return PaperAlertRun(
        new_papers=paper_list,
        errors=[],
        cached_count=0,
        candidate_count=len(paper_list),
        source_count=1,
        candidate_papers=paper_list,
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
        app = PaperAlertDashboard(_build_run(paper), open_url=fake_open)
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
        app = PaperAlertDashboard(_build_run(first, second))
        async with app.run_test() as pilot:
            await pilot.pause()
            status = app.query_one("#selection-status", Static)
            assert first.title in str(status.renderable)
            await pilot.press("down")
            status = app.query_one("#selection-status", Static)
            assert second.title in str(status.renderable)

    asyncio.run(exercise())
