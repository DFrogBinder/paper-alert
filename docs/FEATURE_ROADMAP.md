# Feature Roadmap

This is the current feature brainstorm for `paper-alert`, grouped by product value. The first three items are now implemented.

## Implemented

1. Canonical paper merging
   Merge overlapping records from arXiv, PubMed, bioRxiv, medRxiv, Crossref, and Semantic Scholar into one paper when stable identifiers line up.
2. Triage states
   Persist `new`, `saved`, `dismissed`, and `later` states so papers can move from "discovered" to an actionable workflow.
3. Local searchable archive
   Store canonical papers in a local SQLite archive and support offline search/filter/update flows from the CLI.

## High-Value Next Features

4. Relevance scoring with match explanations
   Rank papers by relevance and show why they matched, for example title hit, abstract hit, DOI merge, or source agreement.
5. Multi-profile watchlists
   Support multiple independent keyword/source profiles such as `core-ti`, `clinical`, `modeling`, and `safety`.
6. Version and publication tracking
   Detect arXiv version bumps, preprint-to-journal transitions, new DOI assignment, or meaningful metadata changes.
7. Digest modes
   Add daily and weekly digest outputs, plus thresholds like "only alert when score >= X".
8. Citation and related-paper expansion
   Starting from one strong hit, pull adjacent papers from citation graphs or related-work endpoints.

## Nice Follow-Ups

9. Optional AI summaries and clustering
   Generate short summaries and group papers by theme to reduce scanning time.
10. Export and integration features
    Support BibTeX export, Markdown notes, email delivery, chat notifications, or knowledge-base sync.
11. Interactive dashboard triage
    Let users change triage state inside the Textual dashboard instead of via CLI commands.
