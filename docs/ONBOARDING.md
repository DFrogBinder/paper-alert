# Paper Alert Onboarding

This project is a small CLI that checks several paper APIs for temporal interference-related publications, compares the results against a local seen-store, and renders a compact startup summary banner. When you want details, it can also print paper lists or open a Textual dashboard.

If you only need the mental model, it is this:

1. `ppl` / `python -m paper_alert` builds config from environment variables and CLI flags.
2. The service layer asks each enabled source adapter for papers.
3. Results are normalized into a shared `Paper` model.
4. The seen-store filters out anything already reported.
5. The CLI renders a startup banner by default, or explicit detail views when you ask for them.

## First 15 Minutes

1. Create an environment and install the package:
   ```sh
   conda env create -f environment.yml
   conda activate paper-alert
   ```
   Or:
   ```sh
   python3 -m venv .venv
   . .venv/bin/activate
   pip install -e .[dev]
   ```
2. Set a real user agent before hitting public APIs:
   ```sh
   export PAPER_ALERT_USER_AGENT="PaperAlert/1.0 (+https://example.com; contact: you@example.com)"
   ```
3. Run the CLI once with errors enabled:
   ```sh
   ppl --show-errors
   ```
4. Run tests:
   ```sh
   pytest -q
   ```

If you want the most verbose manual run, use:

```sh
ppl --show-summary --show-progress --show-errors
```

## What It Does

The tool is optimized for shell startup. Its intended use is to run from `.zshrc` or another shell init file, stay quiet when there is nothing new, and show a compact styled summary when new papers appear.

It currently queries these sources:

- `arxiv`
- `pubmed`
- `biorxiv`
- `medrxiv`
- `crossref`
- `semanticscholar`

Each source adapter is responsible for:

- building a source-specific query,
- calling the remote API,
- converting each result into `Paper(source, identifier, title, url, published)`,
- applying a final keyword filter before returning results.

## Request Flow

Use these files in this order when you need to understand or change behavior:

- [paper_alert/__main__.py](/home/boyan/sandbox/paper-alert/paper_alert/__main__.py): module entry point.
- [paper_alert/cli.py](/home/boyan/sandbox/paper-alert/paper_alert/cli.py): argument parsing, env override application, output mode selection.
- [paper_alert/ui.py](/home/boyan/sandbox/paper-alert/paper_alert/ui.py): Rich renderables for the startup banner, paper tables, and warnings.
- [paper_alert/textual_dashboard.py](/home/boyan/sandbox/paper-alert/paper_alert/textual_dashboard.py): Textual dashboard wrapper around the Rich renderables.
- [paper_alert/config.py](/home/boyan/sandbox/paper-alert/paper_alert/config.py): config loading from environment.
- [paper_alert/service.py](/home/boyan/sandbox/paper-alert/paper_alert/service.py): orchestration, dedupe, sort, seen-store interaction.
- [paper_alert/aggregator.py](/home/boyan/sandbox/paper-alert/paper_alert/aggregator.py): per-source dispatch and error collection.
- [paper_alert/sources/](/home/boyan/sandbox/paper-alert/paper_alert/sources): API-specific fetchers and parsing logic.
- [paper_alert/store.py](/home/boyan/sandbox/paper-alert/paper_alert/store.py): JSON-backed state for previously seen papers.
- [paper_alert/models.py](/home/boyan/sandbox/paper-alert/paper_alert/models.py): canonical `Paper` model.
- [paper_alert/http.py](/home/boyan/sandbox/paper-alert/paper_alert/http.py): shared HTTP helpers and fetch error type.
- [paper_alert/utils.py](/home/boyan/sandbox/paper-alert/paper_alert/utils.py): date parsing, title cleaning, keyword matching.

## Repository Tour

- [README.md](/home/boyan/sandbox/paper-alert/README.md): user-facing setup and usage.
- [environment.yml](/home/boyan/sandbox/paper-alert/environment.yml): Conda environment definition.
- [pyproject.toml](/home/boyan/sandbox/paper-alert/pyproject.toml): package metadata and dev dependencies.
- [tests/test_service.py](/home/boyan/sandbox/paper-alert/tests/test_service.py): service-level behavior around dedupe, sorting, and persistence.
- [tests/test_store.py](/home/boyan/sandbox/paper-alert/tests/test_store.py): store persistence behavior.

## Configuration Surface

Environment variables:

- `PAPER_ALERT_KEYWORDS`: comma-separated keyword list.
- `PAPER_ALERT_SOURCES`: comma-separated source IDs.
- `PAPER_ALERT_MAX_RESULTS`: per-source fetch limit.
- `PAPER_ALERT_STORE`: seen-store path.
- `PAPER_ALERT_LOOKBACK_DAYS`: bioRxiv and medRxiv date window.
- `PAPER_ALERT_SEMANTIC_SCHOLAR_KEY`: optional Semantic Scholar API key.
- `PAPER_ALERT_USER_AGENT`: HTTP user agent used for all outbound requests.

CLI flags:

- `--keywords`
- `--sources`
- `--max-results`
- `--store`
- `--quiet-if-none`
- `--show-errors`
- `--show-summary`
- `--show-progress`
- `--show-new`
- `--show-candidate` / `--show-candidates`
- `--dashboard` / `--app`

Precedence is simple: `PaperAlertConfig.from_env()` loads environment defaults first, then [paper_alert/cli.py](/home/boyan/sandbox/paper-alert/paper_alert/cli.py) applies CLI overrides with `dataclasses.replace`.

## Current Behavior That Matters

- Deduplication is done on `Paper.key`, which is just `"{source}:{identifier}"`.
- New papers are sorted newest-first before display.
- The default run intentionally favors a startup summary banner over paper titles so shell initialization stays compact.
- `--show-new` prints the full new-paper list for the current run.
- `--show-candidate` / `--show-candidates` prints the deduplicated candidate-paper list, including already-seen items.
- `--dashboard` / `--app` opens the Textual dashboard when the `textual` dependency is installed.
- The seen-store is written only when at least one new paper is found.
- If the seen-store JSON is unreadable, the CLI warns and treats it as empty for that run.
- Numeric config inputs are validated early, both from CLI flags and environment variables.
- Source failures do not abort the whole run; they are collected and optionally printed as warnings.
- `PAPER_ALERT_USER_AGENT` is resolved at request time, not module import time.
- arXiv, Crossref, and Semantic Scholar keyword checks consider summary or abstract text, while PubMed no longer drops upstream matches because of title-only filtering.
- `--show-summary` prints a compact status line with source count, candidate count, new-paper count, and cached-count state.
- `--show-progress` emits prefixed progress lines while sources are being checked.

## Common Changes

Change the default search terms:

- Edit `DEFAULT_KEYWORDS` in [paper_alert/constants.py](/home/boyan/sandbox/paper-alert/paper_alert/constants.py).

Add or remove a source:

1. Implement a fetcher in [paper_alert/sources/](/home/boyan/sandbox/paper-alert/paper_alert/sources).
2. Export it from [paper_alert/sources/__init__.py](/home/boyan/sandbox/paper-alert/paper_alert/sources/__init__.py).
3. Register it in `FETCHERS` inside [paper_alert/aggregator.py](/home/boyan/sandbox/paper-alert/paper_alert/aggregator.py).
4. Add tests with mocked HTTP payloads.

Change terminal output:

- Edit [paper_alert/ui.py](/home/boyan/sandbox/paper-alert/paper_alert/ui.py) for banner/panel styling.
- Edit [paper_alert/textual_dashboard.py](/home/boyan/sandbox/paper-alert/paper_alert/textual_dashboard.py) for the interactive dashboard layout.

Change state persistence:

- Edit [paper_alert/store.py](/home/boyan/sandbox/paper-alert/paper_alert/store.py).

## Known Problems And Improvements

These are the first places worth improving if this project grows:

- Source calls are fully sequential. [paper_alert/aggregator.py](/home/boyan/sandbox/paper-alert/paper_alert/aggregator.py) walks the source list one by one, so a slow API can noticeably delay shell startup.
- Network resilience is intentionally minimal. [paper_alert/http.py](/home/boyan/sandbox/paper-alert/paper_alert/http.py) has timeouts and a small polite delay, but no retries, exponential backoff, or source-specific throttling.
- Seen-store writes are not atomic. [paper_alert/store.py](/home/boyan/sandbox/paper-alert/paper_alert/store.py) writes JSON directly to the final path, so an interrupted write could still corrupt the file even though corruption is now surfaced on the next run.
- Unknown source names are handled late. [paper_alert/aggregator.py](/home/boyan/sandbox/paper-alert/paper_alert/aggregator.py) warns and skips unknown IDs at runtime rather than validating them during CLI/config parsing.
- Tests are now much better targeted, but they are still unit-style tests with mocked payloads. The repository still lacks live integration checks against real APIs.

## Suggested Next Work

If you want the highest-return improvements, do these first:

1. Make seen-store writes atomic with a temp file plus rename.
2. Add a retry/backoff strategy for transient HTTP failures.
3. Decide whether shell-startup latency is acceptable or whether source fetches should be parallelized.
4. Validate source names earlier so typos fail fast.
5. Add optional integration checks that can be run manually against the live APIs.
