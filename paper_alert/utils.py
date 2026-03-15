from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Iterable, Sequence
from urllib.parse import urlsplit, urlunsplit


ISO_FORMATS = (
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%d",
)


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    for fmt in ISO_FORMATS:
        try:
            return normalize_datetime(datetime.strptime(value, fmt))
        except ValueError:
            continue
    return None


def parse_pubmed_sortdate(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    for fmt in ("%Y/%m/%d %H:%M", "%Y/%m/%d %H:%M:%S"):
        try:
            return normalize_datetime(datetime.strptime(value, fmt))
        except ValueError:
            continue
    return parse_datetime(value)


def clean_title(title: str | None) -> str:
    if not title:
        return "Untitled"
    title = re.sub(r"\s+", " ", title)
    return title.strip()


def stable_title_key(title: str | None) -> str:
    cleaned = clean_title(title).lower()
    slug = re.sub(r"[^a-z0-9]+", "-", cleaned).strip("-")
    return slug or "untitled"


def normalize_doi(value: str | None) -> str | None:
    if not value:
        return None
    doi = value.strip()
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE)
    doi = doi.lower()
    return doi or None


def normalize_arxiv_id(value: str | None) -> str | None:
    if not value:
        return None
    raw = value.strip()
    raw = re.sub(r"^https?://arxiv\.org/(?:abs|pdf)/", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"^arxiv:", "", raw, flags=re.IGNORECASE)
    raw = raw.removesuffix(".pdf")
    raw = re.sub(r"v\d+$", "", raw, flags=re.IGNORECASE)
    raw = raw.strip().lower()
    return raw or None


def normalize_url(value: str | None) -> str | None:
    if not value:
        return None
    raw = value.strip()
    parsed = urlsplit(raw)
    if not parsed.scheme and not parsed.netloc:
        return raw.rstrip("/").lower() or None
    normalized = urlunsplit(
        (
            parsed.scheme.lower() or "https",
            parsed.netloc.lower(),
            parsed.path.rstrip("/"),
            parsed.query,
            "",
        )
    )
    return normalized or None


def matches_keywords(text: str, keywords: Iterable[str]) -> bool:
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def parse_date_parts(parts: Sequence[Sequence[int]] | None) -> datetime | None:
    if not parts:
        return None
    first = list(parts[0])
    if not first:
        return None
    year = first[0]
    month = first[1] if len(first) >= 2 else 1
    day = first[2] if len(first) >= 3 else 1
    try:
        return normalize_datetime(datetime(year, month, day))
    except ValueError:
        return None


def normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)
