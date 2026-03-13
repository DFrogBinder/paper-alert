from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path
from typing import Iterable, Sequence

from .config import PaperAlertConfig
from .models import Paper
from .service import PaperAlertRun, run_paper_alert


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


def _print_paper_list(
    title: str,
    papers: Iterable[Paper],
    *,
    max_display: int | None = None,
) -> None:
    papers = list(papers)
    total = len(papers)
    displayed = papers if max_display is None else papers[:max_display]
    shown_label = (
        f"showing {len(displayed)} of {total}"
        if total > len(displayed)
        else f"{total} shown"
    )

    print("=" * 72)
    print(f"{title} — {shown_label}")
    print("=" * 72)
    for index, paper in enumerate(displayed, start=1):
        date = paper.published.strftime("%Y-%m-%d") if paper.published else "date unknown"
        print(f"{index}. {paper.title}")
        print(f"   Source: {paper.source} | Published: {date}")
        print()
    if max_display is not None and total > len(displayed):
        remaining = total - len(displayed)
        suffix = "paper" if remaining == 1 else "papers"
        print(f"...and {remaining} more {suffix}.")
    print("=" * 72)


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
        help="Do not print anything when no new papers are found.",
    )
    parser.add_argument(
        "--show-errors",
        action="store_true",
        help="Display warnings for sources that failed during the fetch phase.",
    )
    parser.add_argument(
        "--show-summary",
        action="store_true",
        help="Print a one-line summary even when there are no new papers.",
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
    new_papers = run.new_papers
    candidate_papers = run.candidate_papers
    errors = run.errors
    always_show = [error for error in errors if _should_always_show_error(error)]
    optional_errors = [error for error in errors if not _should_always_show_error(error)]
    showed_candidates = False

    if args.show_candidates and candidate_papers:
        _print_paper_list("Candidate Papers", candidate_papers)
        showed_candidates = True

    if not new_papers:
        if args.show_summary:
            print(_format_summary(run))
        elif not args.quiet_if_none and not showed_candidates:
            print("No new temporal interference papers detected.")
        if always_show:
            _print_errors(always_show)
        if args.show_errors and optional_errors:
            _print_errors(optional_errors)
        return 0

    _print_banner(new_papers)
    if args.show_summary:
        print(_format_summary(run))
    if always_show:
        _print_errors(always_show)
    if args.show_errors and optional_errors:
        _print_errors(optional_errors)
    return 0


def _print_banner(papers: Iterable[Paper]) -> None:
    _print_paper_list("New Temporal Interference Papers", papers, max_display=3)


def _print_errors(errors: Iterable[str]) -> None:
    print("Warnings during fetch:")
    for err in errors:
        print(f" - {err}")


if __name__ == "__main__":
    raise SystemExit(main())
