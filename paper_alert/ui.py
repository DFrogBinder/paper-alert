from __future__ import annotations

from typing import Iterable

from rich import box
from rich.columns import Columns
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .models import Paper
from .service import PaperAlertRun

ACCENT = "#60a5fa"
SUCCESS = "#34d399"
WARNING = "#fbbf24"
DANGER = "#f87171"
MUTED = "#94a3b8"


def build_summary_banner(run: PaperAlertRun) -> Panel:
    new_count = len(run.new_papers)
    if new_count:
        status = Text(f"{new_count} new paper{'s' if new_count != 1 else ''} ready to review", style=f"bold {WARNING}")
    else:
        status = Text("Up to date across your tracked sources", style=f"bold {SUCCESS}")

    metrics = Columns(
        [
            _metric_card("Sources", run.source_count, ACCENT),
            _metric_card("Candidates", run.candidate_count, ACCENT),
            _metric_card("New", new_count, SUCCESS if new_count == 0 else WARNING),
            _metric_card("Cached", run.cached_count, "#94a3b8"),
        ],
        equal=True,
        expand=True,
    )

    body = [
        status,
        Text("Temporal interference literature monitor", style=MUTED),
        metrics,
    ]
    if run.errors:
        body.append(
            Text(
                f"{len(run.errors)} warning{'s' if len(run.errors) != 1 else ''} captured. Re-run with --show-errors for details.",
                style=f"bold {WARNING}",
            )
        )
    if new_count:
        body.append(
            Text(
                "Inspect details with `ppl --show-new` or `ppl --show-candidate --show-summary`.",
                style=MUTED,
            )
        )

    return Panel(
        Group(*body),
        title="Paper Alert",
        subtitle="startup summary",
        border_style=ACCENT,
        box=box.ROUNDED,
        padding=(1, 2),
    )


def build_papers_panel(title: str, papers: Iterable[Paper], *, empty_message: str) -> Panel:
    papers = list(papers)
    if not papers:
        return Panel(
            Text(empty_message, style=MUTED),
            title=title,
            border_style=ACCENT,
            box=box.ROUNDED,
            padding=(1, 2),
        )

    table = Table(expand=True, box=box.SIMPLE_HEAVY, show_edge=False)
    table.add_column("Published", style="#dbeafe", no_wrap=True)
    table.add_column("Source", style=ACCENT, no_wrap=True)
    table.add_column("Title", style="#f8fafc", ratio=1)
    for paper in papers:
        published = paper.published.strftime("%Y-%m-%d") if paper.published else "date unknown"
        table.add_row(published, paper.source, paper.title)

    return Panel(
        table,
        title=title,
        border_style=ACCENT,
        box=box.ROUNDED,
        padding=(0, 1),
    )


def build_errors_panel(errors: Iterable[str]) -> Panel:
    messages = list(errors)
    if not messages:
        return Panel(
            Text("No warnings recorded.", style=MUTED),
            title="Warnings",
            border_style=DANGER,
            box=box.ROUNDED,
            padding=(1, 2),
        )

    content = Group(*(Text(f"- {message}", style=DANGER) for message in messages))
    return Panel(
        content,
        title="Warnings",
        border_style=DANGER,
        box=box.ROUNDED,
        padding=(1, 2),
    )


def _metric_card(label: str, value: int, border_style: str) -> Panel:
    grid = Table.grid(expand=True)
    grid.add_column(justify="center")
    grid.add_row(Text(str(value), style=f"bold {border_style}"))
    grid.add_row(Text(label.upper(), style=MUTED))
    return Panel(
        grid,
        border_style=border_style,
        box=box.ROUNDED,
        padding=(0, 1),
    )
