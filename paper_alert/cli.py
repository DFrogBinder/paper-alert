from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path
from typing import Sequence

from rich.console import Console

from .constants import TRIAGE_STATES
from .config import PaperAlertConfig, normalize_sources
from .service import PaperAlertRun, run_paper_alert
from .store import SeenStore, StoreError
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


def _format_archive_summary(count: int) -> str:
    return f"paper-alert: {count} archived papers matched"


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
        help="Override the path to the SQLite archive database.",
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
    parser.add_argument(
        "--show-archive",
        action="store_true",
        help="Search the local archive without querying remote sources.",
    )
    parser.add_argument(
        "--search",
        help="Filter archive results by title, canonical id, or source.",
    )
    parser.add_argument(
        "--state",
        choices=TRIAGE_STATES,
        help="Filter archive results by triage state.",
    )
    parser.add_argument(
        "--set-state",
        nargs=2,
        metavar=("CANONICAL_ID", "STATE"),
        help="Update the triage state for a canonical paper id.",
    )
    args = parser.parse_args(argv)

    archive_only_flags = (
        args.quiet_if_none,
        args.show_errors,
        args.show_progress,
        args.show_new,
        args.show_candidates,
        args.dashboard,
    )
    if (args.search or args.state) and not args.show_archive:
        parser.error("--search and --state require --show-archive")
    if args.show_archive and any(archive_only_flags):
        parser.error("--show-archive cannot be combined with fetch-only display flags")
    if args.set_state:
        _, triage_state = args.set_state
        if triage_state.lower() not in TRIAGE_STATES:
            parser.error(
                f"--set-state STATE must be one of {', '.join(TRIAGE_STATES)}, got {triage_state!r}"
            )
        if any(archive_only_flags):
            parser.error("--set-state cannot be combined with fetch-only display flags")

    try:
        config = PaperAlertConfig.from_env()
    except ValueError as exc:
        parser.error(str(exc))
    overrides = {}
    keywords_override = _parse_csv(args.keywords)
    sources_override = None
    if args.sources is not None:
        raw_sources = _parse_csv(args.sources)
        if not raw_sources:
            parser.error("--sources must contain at least one source")
        try:
            sources_override = normalize_sources(raw_sources)
        except ValueError as exc:
            parser.error(str(exc))
    if keywords_override:
        overrides["keywords"] = keywords_override
    if sources_override is not None:
        overrides["sources"] = sources_override
    if args.max_results is not None:
        overrides["max_results"] = args.max_results
    if args.store:
        overrides["store_path"] = Path(args.store).expanduser()
    if overrides:
        config = replace(config, **overrides)

    if args.show_archive or args.set_state:
        return _run_archive_mode(
            config,
            args.show_archive,
            args.search,
            args.state,
            args.set_state,
            args.show_summary,
        )

    progress = _print_progress if args.show_progress else None
    try:
        run = run_paper_alert(config, progress=progress)
    except StoreError as exc:
        print(f"paper-alert: {exc}", file=sys.stderr)
        return 1
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


def _run_archive_mode(
    config: PaperAlertConfig,
    show_archive: bool,
    search: str | None,
    state: str | None,
    set_state_args: Sequence[str] | None,
    show_summary: bool,
) -> int:
    try:
        store = SeenStore(config.store_path)
        console = Console(highlight=False)

        if set_state_args is not None:
            canonical_id, triage_state = set_state_args[0], set_state_args[1].lower()
            updated = store.set_triage_state(canonical_id, triage_state)
            if not updated:
                print(f"paper-alert: no archived paper found for {canonical_id!r}", file=sys.stderr)
                return 1
            print(f"paper-alert: updated {canonical_id} -> {triage_state}")

        if show_archive:
            archive_papers = store.query_archive(search=search, triage_state=state)
            console.print(
                build_papers_panel(
                    "Archive",
                    archive_papers,
                    empty_message="No archived papers matched the current query.",
                    show_triage=True,
                    show_canonical_id=True,
                )
            )
            if show_summary:
                print(_format_archive_summary(len(archive_papers)))

        if store.warnings:
            console.print(build_errors_panel(store.warnings))
        return 0
    except StoreError as exc:
        print(f"paper-alert: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
