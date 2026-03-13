from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable, Sequence


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
            dt = datetime.strptime(value, fmt)
            if not dt.tzinfo:
                return dt
            return dt.astimezone(tz=None)
        except ValueError:
            continue
    return None


def parse_pubmed_sortdate(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    for fmt in ("%Y/%m/%d %H:%M", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return parse_datetime(value)


def clean_title(title: str | None) -> str:
    if not title:
        return "Untitled"
    title = re.sub(r"\s+", " ", title)
    return title.strip()


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
        return datetime(year, month, day)
    except ValueError:
        return None
