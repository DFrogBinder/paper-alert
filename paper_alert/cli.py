from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path
from typing import Sequence

from rich.console import Console

from .config import PaperAlertConfig
from .service import PaperAlertRun, run_paper_alert
from .ui import build_errors_panel, build_papers_panel, build_summary_banner


def _parse_csv(raw: str | None) -> tuple[str, ...] | None:
    if raw is None:
        return None
    items = [item.strip() for item in raw.split(",") if item.strip()]
    return tuple(items) if items else None


def _positive_int(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"expected an integer, got {raw!r}") from exc
    if value < 1:
        raise argparse.ArgumentTypeError("expected an integer greater than or equal to 1")
    return value


def _should_always_show_error(error: str) -> bool:
    return error.startswith("store:")


def _format_summary(run: PaperAlertRun) -> str:
    new_count = len(run.new_papers)
    return (
        "paper-alert: "
        f"{run.source_count} sources checked, "
        f"{run.candidate_count} candidate papers, "
        f"{new_count} new, "
        f"{run.cached_count} cached"
    )


def _print_progress(message: str) -> None:
    print(f"[paper-alert] {message}")


def _run_dashboard(run: PaperAlertRun) -> int:
    try:
        from .textual_dashboard import run_dashboard
    except ImportError:
        print(
            "The Textual dashboard requires the 'textual' package. Reinstall with `pip install -e .`.",
            file=sys.stderr,
        )
        return 1

    run_dashboard(run)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Check for new temporal interference papers across arXiv, PubMed, "
            "bioRxiv/medRxiv, Crossref, and Semantic Scholar."
        )
    )
    parser.add_argument(
        "--keywords",
        help="Comma-separated list of keywords to override the default set.",
    )
    parser.add_argument(
        "--max-results",
        type=_positive_int,
        help="Maximum results to request per source (default comes from config).",
    )
    parser.add_argument(
        "--sources",
        help="Comma-separated list of sources to enable (e.g. arxiv,pubmed,medrxiv).",
    )
    parser.add_argument(
        "--store",
        help="Override the path to the JSON file that tracks seen papers.",
    )
    parser.add_argument(
        "--quiet-if-none",
        action="store_true",
        help="Suppress the startup banner when no new papers are found.",
    )
    parser.add_argument(
        "--show-errors",
        action="store_true",
        help="Display warnings for sources that failed during the fetch phase.",
    )
    parser.add_argument(
        "--show-summary",
        action="store_true",
        help="Print a one-line summary alongside any banner or detail output.",
    )
    parser.add_argument(
        "--show-progress",
        action="store_true",
        help="Print source-by-source progress while the fetch is running.",
    )
    parser.add_argument(
        "--show-candidate",
        "--show-candidates",
        dest="show_candidates",
        action="store_true",
        help="Print deduplicated candidate papers before filtering against the seen-store.",
    )
    parser.add_argument(
        "--show-new",
        action="store_true",
        help="Print the new papers captured in this run.",
    )
    parser.add_argument(
        "--dashboard",
        "--app",
        dest="dashboard",
        action="store_true",
        help="Open the Textual dashboard for interactive inspection.",
    )
    args = parser.parse_args(argv)

    try:
        config = PaperAlertConfig.from_env()
    except ValueError as exc:
        parser.error(str(exc))
    overrides = {}
    keywords_override = _parse_csv(args.keywords)
    sources_override = _parse_csv(args.sources)
    if keywords_override:
        overrides["keywords"] = keywords_override
    if sources_override:
        overrides["sources"] = tuple(source.lower() for source in sources_override)
    if args.max_results is not None:
        overrides["max_results"] = args.max_results
    if args.store:
        overrides["store_path"] = Path(args.store).expanduser()
    if overrides:
        config = replace(config, **overrides)

    progress = _print_progress if args.show_progress else None
    run = run_paper_alert(config, progress=progress)
    if args.dashboard:
        return _run_dashboard(run)

    console = Console(highlight=False)
    new_papers = run.new_papers
    candidate_papers = run.candidate_papers
    errors = run.errors
    always_show = [error for error in errors if _should_always_show_error(error)]
    optional_errors = [error for error in errors if not _should_always_show_error(error)]
    detail_requested = args.show_new or args.show_candidates

    if not detail_requested and not (args.quiet_if_none and not new_papers):
        console.print()
        console.print(build_summary_banner(run))

    if args.show_summary:
        print(_format_summary(run))
    if args.show_new:
        console.print(
            build_papers_panel(
                "New Papers",
                new_papers,
                empty_message="No new papers in this run.",
            )
        )
    if args.show_candidates:
        console.print(
            build_papers_panel(
                "Candidate Papers",
                candidate_papers,
                empty_message="No candidate papers matched the current query.",
            )
        )
    if always_show:
        console.print(build_errors_panel(always_show))
    if args.show_errors and optional_errors:
        console.print(build_errors_panel(optional_errors))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
