from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class Paper:
    """Canonical representation for fetched papers."""

    source: str
    identifier: str
    title: str
    url: str
    published: Optional[datetime]

    @property
    def key(self) -> str:
        return f"{self.source}:{self.identifier}"
