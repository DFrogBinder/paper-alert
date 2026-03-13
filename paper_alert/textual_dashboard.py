from __future__ import annotations

from .service import PaperAlertRun
from .ui import build_errors_panel, build_papers_panel, build_summary_banner


def run_dashboard(run: PaperAlertRun) -> None:
    from textual.app import App, ComposeResult
    from textual.containers import VerticalScroll
    from textual.widgets import Footer, Header, Static

    class PaperAlertDashboard(App[None]):
        CSS = """
        Screen {
            background: #08111b;
            color: #e2e8f0;
        }

        Header {
            background: #0f172a;
            color: #e2e8f0;
        }

        Footer {
            background: #0f172a;
            color: #e2e8f0;
        }

        VerticalScroll {
            padding: 1 2;
        }

        Static {
            margin: 0 0 1 0;
        }
        """

        BINDINGS = [("q", "quit", "Quit"), ("escape", "quit", "Quit")]

        def compose(self) -> ComposeResult:
            yield Header(show_clock=False)
            with VerticalScroll():
                yield Static(build_summary_banner(run))
                yield Static(
                    build_papers_panel(
                        "New Papers",
                        run.new_papers,
                        empty_message="No new papers in this run.",
                    )
                )
                yield Static(
                    build_papers_panel(
                        "Candidate Papers",
                        run.candidate_papers,
                        empty_message="No candidate papers matched the current query.",
                    )
                )
                if run.errors:
                    yield Static(build_errors_panel(run.errors))
            yield Footer()

    PaperAlertDashboard().run()
