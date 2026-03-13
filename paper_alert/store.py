from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Set

from .models import Paper


class SeenStore:
    """JSON-backed store that tracks seen paper identifiers."""

    def __init__(self, path: Path):
        self.path = path
        self._warnings: list[str] = []

    @property
    def warnings(self) -> list[str]:
        return list(self._warnings)

    def _warn(self, message: str) -> None:
        if message not in self._warnings:
            self._warnings.append(message)

    def _read(self) -> Set[str]:
        if not self.path.exists():
            return set()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            self._warn(
                f"store: seen-store at {self.path} contains invalid JSON; treating it as empty"
            )
            return set()
        if isinstance(payload, dict) and isinstance(payload.get("seen"), list):
            return set(str(item) for item in payload["seen"])
        if isinstance(payload, list):
            return set(str(item) for item in payload)
        return set()

    def load(self) -> Set[str]:
        return self._read()

    def save(self, seen: Iterable[str]) -> None:
        data = {"seen": sorted(set(seen))}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

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
        seen = self.load()
        new_papers: list[Paper] = []
        for paper in papers:
            if paper.key not in seen:
                new_papers.append(paper)
                seen.add(paper.key)
        if new_papers:
            self.save(seen)
        return new_papers
