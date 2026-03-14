from __future__ import annotations

import webbrowser
from typing import Callable

from .models import Paper
from .service import PaperAlertRun
from .ui import build_errors_panel


def _format_source_label(source: str) -> str:
    labels = {
        "arxiv": "arXiv",
        "pubmed": "PubMed",
        "biorxiv": "bioRxiv",
        "medrxiv": "medRxiv",
        "semanticscholar": "Semantic Scholar",
        "crossref": "Crossref",
    }
    return labels.get(source.lower(), source.title())


def _format_published_date(paper: Paper) -> str:
    return paper.published.strftime("%Y-%m-%d") if paper.published else "Date unavailable"


def _summary_headline(run: PaperAlertRun) -> str:
    new_count = len(run.new_papers)
    if new_count:
        return f"{new_count} new paper{'s' if new_count != 1 else ''} ready to review."
    return "Up to date across your tracked sources."


def _paper_details_text(paper: Paper | None) -> str:
    if paper is None:
        return "No paper selected.\nChoose a row, then press Enter or click to open the paper page."
    return (
        f"Title: {paper.title}\n"
        f"Source: {_format_source_label(paper.source)}\n"
        f"Published: {_format_published_date(paper)}\n"
        f"URL: {paper.url}\n"
        "Enter or click opens the selected paper in your browser."
    )


def _open_in_browser(url: str) -> bool:
    try:
        return bool(webbrowser.open(url, new=2, autoraise=False))
    except webbrowser.Error:
        return False


def _count_label(title: str, count: int) -> str:
    return f"{title} ({count})"


def _first_paper(run: PaperAlertRun) -> Paper | None:
    if run.new_papers:
        return run.new_papers[0]
    if run.candidate_papers:
        return run.candidate_papers[0]
    return None


def _initial_tab_id(run: PaperAlertRun) -> str:
    if run.new_papers:
        return "new-papers-pane"
    if run.candidate_papers:
        return "candidate-papers-pane"
    if run.errors:
        return "warnings-pane"
    return "new-papers-pane"


def _paper_title_for_notification(paper: Paper) -> str:
    if len(paper.title) <= 72:
        return paper.title
    return f"{paper.title[:69]}..."


def run_dashboard(run: PaperAlertRun) -> None:
    PaperAlertDashboard(run).run()


class PaperTableMixin:
    def paper_from_row_key(self, row_key: object) -> Paper | None:
        raise NotImplementedError

    def highlighted_paper(self) -> Paper | None:
        raise NotImplementedError


def _build_dashboard_class():
    from textual.app import App, ComposeResult
    from textual.containers import Horizontal, Vertical, VerticalScroll
    from textual.widgets import DataTable, Footer, Header, Static, TabPane, TabbedContent

    class PaperTable(DataTable[str], PaperTableMixin):
        def __init__(self, papers: list[Paper], *, id: str) -> None:
            super().__init__(
                show_row_labels=False,
                zebra_stripes=True,
                cursor_type="row",
                cursor_foreground_priority="css",
                cursor_background_priority="css",
                id=id,
                classes="paper-table",
            )
            self._papers_by_key = {paper.key: paper for paper in papers}
            self.add_column("Published", width=12, key="published")
            self.add_column("Source", width=18, key="source")
            self.add_column("Title", key="title")
            for paper in papers:
                self.add_row(
                    _format_published_date(paper),
                    _format_source_label(paper.source),
                    paper.title,
                    key=paper.key,
                )

        def paper_from_row_key(self, row_key: object) -> Paper | None:
            value = getattr(row_key, "value", row_key)
            if value is None:
                return None
            return self._papers_by_key.get(str(value))

        def highlighted_paper(self) -> Paper | None:
            if self.row_count == 0:
                return None
            row_key = self.ordered_rows[self.cursor_coordinate.row].key
            return self.paper_from_row_key(row_key)

    class DashboardApp(App[None]):
        TITLE = "Paper Alert"
        SUB_TITLE = "Interactive Literature Review"

        CSS = """
        Screen {
            background: #07111d;
            color: #dbeafe;
        }

        Header {
            background: #08111d;
            color: #dbeafe;
            border-bottom: tall #1f3651;
        }

        Footer {
            background: #08111d;
            color: #7dd3fc;
            border-top: tall #1f3651;
        }

        #layout {
            height: 1fr;
            layout: horizontal;
            padding: 1 2 1 2;
        }

        #sidebar {
            width: 32;
            min-width: 28;
            max-width: 36;
            margin: 0 1 0 0;
        }

        #workspace {
            width: 1fr;
            height: 1fr;
            layout: vertical;
        }

        .sidebar-card {
            margin: 0 0 1 0;
            padding: 1 2;
            border: round #243b53;
            background: #0b1624;
            color: #cbd5e1;
        }

        #brand-card {
            background: #101d30;
            color: #f8fafc;
            text-style: bold;
        }

        #status-card {
            color: #dbeafe;
        }

        .metric-card {
            text-style: bold;
            color: #f8fafc;
        }

        #controls-card {
            color: #8ea6c0;
        }

        #warnings-card {
            color: #fecdd3;
            border: round #7f1d1d;
            background: #2a1218;
        }

        #paper-tabs {
            height: 1fr;
            margin: 0 0 1 0;
            padding: 0 1 1 1;
            border: round #243b53;
            background: #0b1624;
        }

        ContentTabs {
            background: transparent;
            padding: 0 0 1 0;
        }

        ContentTab {
            background: #101d30;
            color: #7c93ad;
            border: none;
            margin: 0 1 0 0;
            padding: 0 2;
        }

        ContentTab.-active {
            background: #17304c;
            color: #f8fafc;
            text-style: bold;
        }

        TabPane {
            height: 1fr;
            layout: vertical;
            padding: 0;
        }

        .paper-table {
            height: 1fr;
            border: round #243b53;
            background: #091320;
            color: #94a3b8;
        }

        .paper-table > .datatable--header {
            background: #101d30;
            color: #dbeafe;
            text-style: bold;
        }

        .paper-table > .datatable--odd-row {
            color: #8ea6c0;
            background: #091320;
        }

        .paper-table > .datatable--even-row {
            color: #8ea6c0;
            background: #0d1724;
        }

        .paper-table > .datatable--cursor {
            background: #17324d;
            color: #f8fafc;
            text-style: bold;
        }

        .paper-table:focus > .datatable--cursor {
            background: #1f4568;
            color: #f8fafc;
            text-style: bold;
        }

        .empty-state {
            height: 1fr;
            padding: 2 2;
            border: round #243b53;
            background: #091320;
            color: #8ea6c0;
        }

        #selection-status {
            min-height: 5;
            padding: 1 2;
            border: round #1f3651;
            background: #08111d;
            color: #dbeafe;
        }
        """

        BINDINGS = [
            ("q", "quit", "Quit"),
            ("escape", "quit", "Quit"),
            ("tab", "focus_next", "Next Panel"),
            ("shift+tab", "focus_previous", "Prev Panel"),
        ]

        def __init__(
            self,
            run: PaperAlertRun,
            *,
            open_url: Callable[[str], bool] = _open_in_browser,
        ) -> None:
            super().__init__()
            self._run = run
            self._open_url = open_url

        def compose(self) -> ComposeResult:
            yield Header(show_clock=False)
            with Horizontal(id="layout"):
                with VerticalScroll(id="sidebar"):
                    yield Static("Paper Alert", id="brand-card", classes="sidebar-card", markup=False)
                    yield Static(_summary_headline(self._run), id="status-card", classes="sidebar-card", markup=False)
                    yield Static(
                        f"[b]{self._run.source_count}[/b]\nSources tracked",
                        classes="sidebar-card metric-card",
                    )
                    yield Static(
                        f"[b]{self._run.candidate_count}[/b]\nCandidate papers",
                        classes="sidebar-card metric-card",
                    )
                    yield Static(
                        f"[b]{len(self._run.new_papers)}[/b]\nNew this run",
                        classes="sidebar-card metric-card",
                    )
                    yield Static(
                        f"[b]{self._run.cached_count}[/b]\nCached papers",
                        classes="sidebar-card metric-card",
                    )
                    yield Static(
                        "Use Tab to switch panes.\nUse Up and Down to move.\nPress Enter or click a row to open it.",
                        id="controls-card",
                        classes="sidebar-card",
                        markup=False,
                    )
                    if self._run.errors:
                        yield Static(
                            f"{len(self._run.errors)} warning{'s' if len(self._run.errors) != 1 else ''} captured.\nOpen the Warnings tab for details.",
                            id="warnings-card",
                            classes="sidebar-card",
                            markup=False,
                        )
                with Vertical(id="workspace"):
                    with TabbedContent(initial=_initial_tab_id(self._run), id="paper-tabs"):
                        with TabPane(
                            _count_label("New Papers", len(self._run.new_papers)),
                            id="new-papers-pane",
                        ):
                            if self._run.new_papers:
                                yield PaperTable(self._run.new_papers, id="new-papers-table")
                            else:
                                yield Static("No new papers in this run.", classes="empty-state", markup=False)
                        with TabPane(
                            _count_label("Candidate Papers", len(self._run.candidate_papers)),
                            id="candidate-papers-pane",
                        ):
                            if self._run.candidate_papers:
                                yield PaperTable(self._run.candidate_papers, id="candidate-papers-table")
                            else:
                                yield Static(
                                    "No candidate papers matched the current query.",
                                    classes="empty-state",
                                    markup=False,
                                )
                        if self._run.errors:
                            with TabPane(
                                _count_label("Warnings", len(self._run.errors)),
                                id="warnings-pane",
                            ):
                                yield Static(build_errors_panel(self._run.errors))
                    yield Static(
                        _paper_details_text(_first_paper(self._run)),
                        id="selection-status",
                        markup=False,
                    )
            yield Footer()

        def on_mount(self) -> None:
            self._focus_first_table()
            self._update_selection_status(_first_paper(self._run))

        def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
            for table in event.pane.query("PaperTable"):
                table.focus()
                if isinstance(table, PaperTableMixin):
                    self._update_selection_status(table.highlighted_paper())
                return
            self._update_selection_status(None)

        def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
            if isinstance(event.data_table, PaperTableMixin):
                self._update_selection_status(event.data_table.paper_from_row_key(event.row_key))

        def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
            if not isinstance(event.data_table, PaperTableMixin):
                return
            paper = event.data_table.paper_from_row_key(event.row_key)
            self._update_selection_status(paper)
            if paper is None:
                return
            opened = self._open_url(paper.url)
            if opened:
                self.notify(
                    "Opening paper in browser",
                    title=_paper_title_for_notification(paper),
                    timeout=2.5,
                )
                return
            self.notify(
                "Unable to open the paper URL in the system browser",
                title="Browser Launch Failed",
                severity="error",
                timeout=3.5,
            )

        def _focus_first_table(self) -> None:
            for table in self.query("PaperTable"):
                table.focus()
                return

        def _update_selection_status(self, paper: Paper | None) -> None:
            self.query_one("#selection-status", Static).update(_paper_details_text(paper))

    return DashboardApp


PaperAlertDashboard = _build_dashboard_class()
