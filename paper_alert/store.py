from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable, Set

from .constants import DEFAULT_TRIAGE_STATE, TRIAGE_STATES
from .models import Paper

SCHEMA = """
CREATE TABLE IF NOT EXISTS papers (
    canonical_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    identifier TEXT NOT NULL,
    title TEXT NOT NULL,
    primary_url TEXT NOT NULL,
    published TEXT,
    doi TEXT,
    arxiv_id TEXT,
    pmid TEXT,
    triage_state TEXT NOT NULL,
    sources_json TEXT NOT NULL,
    alternate_urls_json TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_papers_triage_state ON papers (triage_state);
CREATE INDEX IF NOT EXISTS idx_papers_last_seen_at ON papers (last_seen_at);
"""


class SeenStore:
    """SQLite-backed archive that tracks canonical papers and triage state."""

    def __init__(self, path: Path):
        self.path = path
        self._warnings: list[str] = []
        self._initialized = False

    @property
    def warnings(self) -> list[str]:
        return list(self._warnings)

    def _warn(self, message: str) -> None:
        if message not in self._warnings:
            self._warnings.append(message)

    def _ensure_database(self) -> None:
        if self._initialized:
            return

        self.path.parent.mkdir(parents=True, exist_ok=True)
        legacy_seen = self._prepare_legacy_migration()
        with sqlite3.connect(self.path) as conn:
            conn.executescript(SCHEMA)
            if legacy_seen:
                self._insert_placeholder_rows(conn, legacy_seen)
        self._initialized = True

    def _prepare_legacy_migration(self) -> set[str] | None:
        if not self.path.exists() or self._is_sqlite_database():
            return None

        raw = self.path.read_text(encoding="utf-8")
        backup_path = self.path.with_suffix(self.path.suffix + ".legacy.json")
        if not backup_path.exists():
            backup_path.write_text(raw, encoding="utf-8")

        seen_keys: set[str] = set()
        if raw.strip():
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                self._warn(
                    f"store: seen-store at {self.path} contains invalid JSON; treating it as empty"
                )
            else:
                if isinstance(payload, dict) and isinstance(payload.get("seen"), list):
                    seen_keys = {str(item) for item in payload["seen"]}
                elif isinstance(payload, list):
                    seen_keys = {str(item) for item in payload}

        self.path.unlink(missing_ok=True)
        if seen_keys:
            self._warn(
                f"store: migrated legacy seen-store at {backup_path} into SQLite archive format"
            )
        return seen_keys

    def _is_sqlite_database(self) -> bool:
        if not self.path.exists():
            return False
        header = self.path.read_bytes()[:16]
        return header == b"SQLite format 3\x00"

    def _connect(self) -> sqlite3.Connection:
        self._ensure_database()
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _insert_placeholder_rows(self, conn: sqlite3.Connection, seen_keys: Iterable[str]) -> None:
        now = self._timestamp()
        for key in sorted(set(seen_keys)):
            source, _, identifier = key.partition(":")
            paper = Paper(
                source=source or "legacy",
                identifier=identifier or key,
                title=key,
                url="",
                published=None,
                triage_state="dismissed",
                canonical_id_override=key,
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO papers (
                    canonical_id, source, identifier, title, primary_url, published,
                    doi, arxiv_id, pmid, triage_state, sources_json, alternate_urls_json,
                    first_seen_at, last_seen_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._paper_row(paper, now=now, first_seen_at=now),
            )

    def _timestamp(self) -> str:
        return datetime.now(UTC).isoformat(timespec="seconds")

    def _serialize_datetime(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None

    def _deserialize_datetime(self, value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    def _paper_row(
        self,
        paper: Paper,
        *,
        now: str,
        first_seen_at: str | None = None,
        triage_state: str | None = None,
    ) -> tuple[object, ...]:
        return (
            paper.canonical_id,
            paper.source,
            paper.identifier,
            paper.title,
            paper.url,
            self._serialize_datetime(paper.published),
            paper.doi,
            paper.arxiv_id,
            paper.pmid,
            triage_state or paper.triage_state or DEFAULT_TRIAGE_STATE,
            json.dumps(list(paper.all_sources)),
            json.dumps(list(paper.all_urls[1:])),
            first_seen_at or now,
            now,
        )

    def _paper_from_row(self, row: sqlite3.Row) -> Paper:
        sources = tuple(json.loads(row["sources_json"]))
        alternate_urls = tuple(json.loads(row["alternate_urls_json"]))
        return Paper(
            source=row["source"],
            identifier=row["identifier"],
            title=row["title"],
            url=row["primary_url"],
            published=self._deserialize_datetime(row["published"]),
            doi=row["doi"],
            arxiv_id=row["arxiv_id"],
            pmid=row["pmid"],
            triage_state=row["triage_state"],
            sources=sources,
            alternate_urls=alternate_urls,
            canonical_id_override=row["canonical_id"],
        )

    def _merge_archive_paper(self, existing: Paper | None, current: Paper) -> Paper:
        if existing is None:
            return current

        published = existing.published
        if current.published and (published is None or current.published > published):
            published = current.published

        sources = _unique_in_order([*existing.all_sources, *current.all_sources])
        urls = _unique_in_order([*existing.all_urls, *current.all_urls])
        primary_url = current.url or existing.url
        alternate_urls = tuple(url for url in urls if url and url != primary_url)
        return Paper(
            source=current.source or existing.source,
            identifier=current.identifier or existing.identifier,
            title=current.title if current.title != "Untitled" else existing.title,
            url=primary_url,
            published=published,
            doi=current.doi or existing.doi,
            arxiv_id=current.arxiv_id or existing.arxiv_id,
            pmid=current.pmid or existing.pmid,
            triage_state=existing.triage_state,
            sources=tuple(sources),
            alternate_urls=alternate_urls,
            canonical_id_override=current.canonical_id,
        )

    def load(self) -> Set[str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT canonical_id FROM papers").fetchall()
        return {str(row["canonical_id"]) for row in rows}

    def count(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS count FROM papers").fetchone()
        return int(row["count"]) if row is not None else 0

    def load_papers(self, canonical_ids: Iterable[str]) -> dict[str, Paper]:
        identifiers = [paper_id for paper_id in canonical_ids if paper_id]
        if not identifiers:
            return {}
        placeholders = ",".join("?" for _ in identifiers)
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM papers WHERE canonical_id IN ({placeholders})",
                identifiers,
            ).fetchall()
        return {str(row["canonical_id"]): self._paper_from_row(row) for row in rows}

    def upsert_papers(self, papers: Iterable[Paper]) -> set[str]:
        paper_list = list(papers)
        if not paper_list:
            return set()

        new_ids: set[str] = set()
        now = self._timestamp()
        with self._connect() as conn:
            for paper in paper_list:
                row = conn.execute(
                    "SELECT * FROM papers WHERE canonical_id = ?",
                    (paper.canonical_id,),
                ).fetchone()
                existing = self._paper_from_row(row) if row is not None else None
                merged = self._merge_archive_paper(existing, paper)
                if existing is None:
                    new_ids.add(merged.canonical_id)
                conn.execute(
                    """
                    INSERT INTO papers (
                        canonical_id, source, identifier, title, primary_url, published,
                        doi, arxiv_id, pmid, triage_state, sources_json, alternate_urls_json,
                        first_seen_at, last_seen_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(canonical_id) DO UPDATE SET
                        source = excluded.source,
                        identifier = excluded.identifier,
                        title = excluded.title,
                        primary_url = excluded.primary_url,
                        published = excluded.published,
                        doi = excluded.doi,
                        arxiv_id = excluded.arxiv_id,
                        pmid = excluded.pmid,
                        triage_state = excluded.triage_state,
                        sources_json = excluded.sources_json,
                        alternate_urls_json = excluded.alternate_urls_json,
                        last_seen_at = excluded.last_seen_at
                    """,
                    self._paper_row(
                        merged,
                        now=now,
                        first_seen_at=row["first_seen_at"] if row is not None else now,
                        triage_state=existing.triage_state if existing is not None else merged.triage_state,
                    ),
                )
        return new_ids

    def query_archive(
        self,
        *,
        search: str | None = None,
        triage_state: str | None = None,
        limit: int = 100,
    ) -> list[Paper]:
        clauses: list[str] = []
        params: list[object] = []
        if search:
            pattern = f"%{search.lower()}%"
            clauses.append(
                "(lower(title) LIKE ? OR lower(canonical_id) LIKE ? OR lower(sources_json) LIKE ?)"
            )
            params.extend([pattern, pattern, pattern])
        if triage_state:
            clauses.append("triage_state = ?")
            params.append(triage_state)

        sql = "SELECT * FROM papers"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY COALESCE(published, last_seen_at) DESC, last_seen_at DESC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._paper_from_row(row) for row in rows]

    def set_triage_state(self, canonical_id: str, triage_state: str) -> bool:
        if triage_state not in TRIAGE_STATES:
            raise ValueError(
                f"triage_state must be one of {', '.join(TRIAGE_STATES)}, got {triage_state!r}"
            )
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE papers SET triage_state = ? WHERE canonical_id = ?",
                (triage_state, canonical_id),
            )
        return cursor.rowcount > 0

    def save(self, seen: Iterable[str]) -> None:
        placeholders = [
            Paper(
                source=str(item).partition(":")[0] or "legacy",
                identifier=str(item).partition(":")[2] or str(item),
                title=str(item),
                url="",
                published=None,
                triage_state="dismissed",
                canonical_id_override=str(item),
            )
            for item in sorted(set(seen))
        ]
        self.upsert_papers(placeholders)

    def filter_new(self, papers: Iterable[Paper]) -> tuple[list[Paper], Set[str]]:
        seen = self.load()
        new_papers: list[Paper] = []
        new_keys: Set[str] = set()
        for paper in papers:
            key = paper.key
            if key in seen:
                continue
            new_papers.append(paper)
            new_keys.add(key)
        return new_papers, seen.union(new_keys)

    def mark_seen(self, papers: Iterable[Paper]) -> list[Paper]:
        existing = self.load()
        paper_list = list(papers)
        new_papers = [paper for paper in paper_list if paper.key not in existing]
        self.upsert_papers(paper_list)
        return new_papers


def _unique_in_order(values: Iterable[str]) -> list[str]:
    unique: list[str] = []
    for value in values:
        if not value or value in unique:
            continue
        unique.append(value)
    return unique
