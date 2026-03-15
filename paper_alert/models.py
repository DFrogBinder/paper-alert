from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .constants import DEFAULT_TRIAGE_STATE
from .utils import normalize_arxiv_id, normalize_doi, normalize_url, stable_title_key


@dataclass(frozen=True)
class Paper:
    """Canonical representation for fetched papers."""

    source: str
    identifier: str
    title: str
    url: str
    published: Optional[datetime]
    doi: str | None = None
    arxiv_id: str | None = None
    pmid: str | None = None
    triage_state: str = DEFAULT_TRIAGE_STATE
    sources: tuple[str, ...] = ()
    alternate_urls: tuple[str, ...] = ()
    canonical_id_override: str | None = None

    @property
    def canonical_id(self) -> str:
        if self.canonical_id_override:
            return self.canonical_id_override

        doi = normalize_doi(self.doi)
        if doi:
            return f"doi:{doi}"

        arxiv_id = normalize_arxiv_id(self.arxiv_id)
        if arxiv_id:
            return f"arxiv:{arxiv_id}"

        if self.pmid:
            return f"pmid:{str(self.pmid).strip()}"

        identifier = self.identifier.strip()
        if identifier:
            return f"{self.source}:{identifier.casefold()}"

        normalized_url = normalize_url(self.url)
        if normalized_url:
            return f"url:{normalized_url}"

        return f"title:{stable_title_key(self.title)}"

    @property
    def key(self) -> str:
        return self.canonical_id

    @property
    def all_sources(self) -> tuple[str, ...]:
        return self.sources or (self.source,)

    @property
    def all_urls(self) -> tuple[str, ...]:
        urls = [self.url, *self.alternate_urls]
        unique_urls: list[str] = []
        for url in urls:
            if not url or url in unique_urls:
                continue
            unique_urls.append(url)
        return tuple(unique_urls)
