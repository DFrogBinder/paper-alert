# Temporal Interference Paper Alert

A lightweight Python utility that queries multiple publication sources for temporal interference-related papers and prints a polished startup banner whenever your shell starts. When you want detail, you can open a Textual dashboard or ask for explicit paper lists from the CLI.

New here: start with [docs/ONBOARDING.md](/home/boyan/sandbox/paper-alert/docs/ONBOARDING.md). It is the shortest path to understanding how the project works, where to change things, and what the current rough edges are. Future-facing ideas live in [docs/FEATURE_ROADMAP.md](/home/boyan/sandbox/paper-alert/docs/FEATURE_ROADMAP.md).

## Features
- Aggregates from arXiv, PubMed, bioRxiv, medRxiv, Crossref, and Semantic Scholar
- Canonically merges overlapping records across sources when DOI, arXiv id, or PMID metadata is available
- Stores a local SQLite archive with per-paper triage state and search support
- Configurable keywords, sources, and quotas via environment variables or CLI flags
- Styled summary banner for `.zshrc` (or any shell init script) usage
- Optional Textual dashboard for manual inspection of new papers, candidates, and warnings
- Offline archive review commands for searching and triaging previously seen papers

## Prerequisites
- Python 3.10+ (tested with 3.12)
- Outbound network access for the public APIs listed above
- Please set a descriptive user-agent via `PAPER_ALERT_USER_AGENT` to comply with API fair-use policies, e.g.
  ```sh
  export PAPER_ALERT_USER_AGENT="PaperAlert/1.0 (+https://github.com/your-handle; contact: you@example.com)"
  ```

## Usage
Run the checker manually:
```sh
ppl
```

If you install the package, the same CLI is also exposed as `paper-alert` and `ppl`.

Common options:
- `--quiet-if-none` – suppress the startup banner when nothing new is found
- `--show-errors` – surface transient fetch problems
- `--show-summary` – print a one-line status summary in addition to the styled output
- `--show-progress` – print source-by-source progress while checking APIs
- `--show-new` – print the new papers captured in the current run
- `--show-candidate` / `--show-candidates` – print the canonical candidate-paper list before archive history filters out already-cached items
- `--dashboard` / `--app` – open the Textual dashboard for interactive inspection
- `--show-archive --search "term"` – query the local archive without hitting remote APIs
- `--show-archive --state saved` – filter archived papers by triage state
- `--set-state <CANONICAL_ID> <STATE>` – update a paper triage state (`new`, `saved`, `dismissed`, `later`)
- `--keywords "kw1,kw2"` – override the keyword list
- `--sources "arxiv,pubmed"` – restrict active sources
- `--max-results 50` – change per-source limit
- `--store ~/.local/share/paper-alert.sqlite3` – move the archive database

All options have environment-variable equivalents:
- `PAPER_ALERT_KEYWORDS`
- `PAPER_ALERT_SOURCES`
- `PAPER_ALERT_MAX_RESULTS`
- `PAPER_ALERT_STORE`
- `PAPER_ALERT_LOOKBACK_DAYS` (bioRxiv/medRxiv window)
- `PAPER_ALERT_SEMANTIC_SCHOLAR_KEY`

## Step-by-step usage
1. Export a descriptive user agent (required by several APIs):
   ```sh
   export PAPER_ALERT_USER_AGENT="PaperAlert/1.0 (+https://github.com/your-handle; contact: you@example.com)"
   ```
2. (Optional) Override defaults with environment variables or CLI flags—e.g. limit sources with `PAPER_ALERT_SOURCES="arxiv,pubmed"` or raise quotas via `--max-results 50`.
3. Run the tool and include `--show-errors` on first use so transient API issues are surfaced:
   ```sh
   ppl --show-errors
   ```
4. Review the banner: the default CLI now renders a compact styled summary instead of dumping titles into the prompt. Use `--show-new`, `--show-candidate`, `--show-archive`, or `--dashboard` when you want detail.
5. The local archive database at your configured `--store` path tracks canonical paper records plus triage state. Use `--show-archive` to review it and `--set-state` to organize it.
6. Once manual runs look good, copy the snippet from the next section into your shell init file so the check executes automatically whenever a terminal opens.

## HOW TO USE
Practical invocations you can copy/paste or adapt:

- **Baseline check with verbose errors** – confirms connectivity and surfaces transient API issues.
  ```sh
  ppl --show-errors
  ```
- **Normal shell-startup run** – prints the styled summary banner and returns immediately.
  ```sh
  ppl
  ```
- **See what the tool is doing and how much state it has cached** – useful when tuning or debugging startup behavior.
  ```sh
  ppl --show-summary --show-progress --show-errors
  ```
- **List new papers for the current run** – good when the startup banner reports fresh results and you want the actual titles.
  ```sh
  ppl --show-new --show-summary
  ```
- **List every deduplicated candidate title, including already-seen papers** – useful when you want to inspect the full fetched set instead of only new items.
  ```sh
  ppl --show-candidate --show-summary
  ```
- **Search the local archive without making network calls** – useful when you want to find an older paper quickly.
  ```sh
  ppl --show-archive --search "field shaping" --show-summary
  ```
- **Mark an archived paper as saved, dismissed, or read later** – triage is keyed by canonical id.
  ```sh
  ppl --set-state doi:10.1000/example saved
  ```
- **Open the Textual dashboard** – interactive view for summary, new papers, candidates, and warnings.
  ```sh
  ppl --dashboard
  ```
- **Focus on two sources with custom keywords and a tighter quota** – helpful when testing changes quickly.
  ```sh
  ppl \
    --keywords "temporal interference,non-invasive neuromodulation" \
    --sources "arxiv,pubmed" \
    --max-results 10
  ```
- **Use an alternate seen-store and stay quiet unless something is new** – good for cron jobs or CI hooks.
  ```sh
  ppl --store ~/.local/share/paper-alert.json --quiet-if-none
  ```
- **One-off run with inline env overrides** – keeps your shell clean while enforcing a compliant user-agent.
  ```sh
  PAPER_ALERT_USER_AGENT="PaperAlert/1.0 (+https://example.com; contact: you@example.com)" \
  PAPER_ALERT_SOURCES="arxiv,crossref,semanticscholar" \
  ppl --show-errors
  ```

## Automatic banner in `.zshrc`
Add the following snippet near the end of your `~/.zshrc` (or other shell init file):
```sh
# Temporal interference paper alert
if command -v ppl >/dev/null 2>&1; then
  {
    ppl --quiet-if-none
  } &!
fi
```
This keeps shell startup simple: the shell prompt returns immediately, and when there is something new you get the styled summary banner as soon as the background check completes. When nothing is new, `--quiet-if-none` keeps startup silent. For manual follow-up, run `ppl --show-new --show-summary`, `ppl --show-candidate --show-summary`, or `ppl --dashboard`.

When previously unseen papers are discovered you'll see a banner like:
```                                                                      
.---------------------------------------------------------------.
| Paper Alert                                      startup summary |
|                                                               |
| 2 new papers ready to review                                  |
| Temporal interference literature monitor                      |
| [Sources] [Candidates] [New] [Cached]                         |
`---------------------------------------------------------------'
```
If no new papers are found the snippet above stays silent.

## How it works
1. Build the keyword query set (default phrases related to temporal interference)
2. Query each configured source with polite delays and a custom user-agent
3. Normalize results to a common `Paper` model (id, title, URL, publication date)
4. Compare against the local archive of canonical papers and triage state
5. Render a startup summary banner and persist newly seen identifiers

## Behavior Notes
- `--max-results` and numeric environment settings are validated before execution; invalid values now fail with a clear CLI error.
- If the existing store path still contains a legacy JSON seen-store, the tool migrates it into the SQLite archive format.
- `PAPER_ALERT_USER_AGENT` is read when requests are made, so environment changes take effect immediately on the next run.
- Candidate dedupe is now canonical when stable ids are available, so matching DOI/arXiv/PMID records from multiple sources collapse into one paper.
- Source matching is less title-biased than before: arXiv, Crossref, and Semantic Scholar also inspect summary or abstract fields, and PubMed trusts the upstream query result instead of re-filtering on title alone.
- The default CLI run now renders a compact summary banner that is designed for shell startup rather than dumping paper titles into the prompt.
- `--show-summary` reports how many sources were checked, how many candidate papers were considered, how many were new, and how many cached identifiers are now stored locally.
- `--show-new` prints the new-paper list for the current run.
- `--show-candidate` / `--show-candidates` prints the canonical candidate-paper list before the archive removes items you have already seen.
- `--show-archive` searches the local archive and `--set-state` updates archived paper triage state without hitting remote APIs.
- `--dashboard` opens the Textual dashboard for manual inspection.

### Code pipeline block diagram
```
┌────────────────────────┐
│ Shell entry (__main__) │
└──────────────┬─────────┘
               │
               ▼
┌──────────────────────────────┐
│ CLI parser + overrides       │ paper_alert/cli.py
│ • argparse flags/env overrides│
│ • builds PaperAlertConfig    │
└──────────────┬───────────────┘
               │ config
               ▼
┌──────────────────────────────┐
│ collect_new_papers service   │ paper_alert/service.py
│ • gather_papers()            │
│ • dedupe + SeenStore         │
│ • sort newest-first          │
└───────┬─────────┬────────────┘
        │         │
        │         ▼
        │   ┌───────────────┐
│   │ ArchiveStore  │ paper_alert/store.py
│   │ mark_seen/save│
│   └───────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│ gather_papers aggregator             │ paper_alert/aggregator.py
│ • Iterate cfg.sources                │
│ • Dispatch per-source fetcher        │
│ • Collect errors                     │
└──────────────┬────────────────────────┘
               │
               ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Source fetchers (paper_alert/sources/*.py)                                 │
│ • Build API queries + keyword filters (arXiv, PubMed, bio/medRxiv,         │
│   Crossref, Semantic Scholar)                                              │
│ • Use utils for parsing/clean titles                                       │
│ • Emit Paper models                                                        │
└──────────────┬─────────────────────────────────────────────────────────────┘
               │ uses
               ▼
┌──────────────────────────────┐
│ HTTP helpers + constants     │ paper_alert/http.py, paper_alert/constants.py
│ • Shared User-Agent, polite delays, JSON/text fetch                        │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│ Paper model                  │ paper_alert/models.py
│ • source/id/title/url/date   │
│ • key property for dedupe    │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│ CLI + UI layer               │ paper_alert/cli.py, paper_alert/ui.py
│ • Startup summary banner     │
│ • Optional detail panels     │
│ • Textual dashboard launcher │
└──────────────────────────────┘
```

The archive is a local SQLite database. Delete the file if you want to re-alert on everything or reset triage history.

## Troubleshooting
- **API rate limits** – make sure you set a meaningful user-agent and, if needed, add sleeps or reduce frequency.
- **Semantic Scholar auth** – set `PAPER_ALERT_SEMANTIC_SCHOLAR_KEY` if you have an API key; otherwise the public tier is used.
- **Proxy / network issues** – run the command with `--show-errors` to see which source failed.

## Development setup
Prefer a Conda environment so the utility (often called from `.zshrc`) stays isolated from your system Python:
```sh
conda create --name paper-alert python=3.12
conda activate paper-alert
pip install -e .[dev]
```
That installation exposes `paper-alert` and `ppl` as shell commands in the active environment.
The development extras install the pinned tooling declared in `pyproject.toml` (currently `pytest==7.4.4`). Runtime UI styling now relies on Textual and its Rich-based render stack.

## Next steps
- Consider wrapping the script in a virtual environment and pinning dependencies if you expand it.
- Add tests or mocks before contributing new features.
