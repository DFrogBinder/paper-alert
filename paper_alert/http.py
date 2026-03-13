from __future__ import annotations

import json
import time
from typing import Any, Dict
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .constants import get_user_agent


class FetchError(RuntimeError):
    pass


def build_query(params: Dict[str, Any]) -> str:
    return urlencode({k: v for k, v in params.items() if v is not None})


def fetch_bytes(url: str, *, headers: Dict[str, str] | None = None, timeout: int = 15) -> bytes:
    req_headers = {"User-Agent": get_user_agent()}
    if headers:
        req_headers.update(headers)
    request = Request(url, headers=req_headers)
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read()
    except HTTPError as exc:  # pragma: no cover - passthrough for runtime
        raise FetchError(f"HTTP {exc.code} while fetching {url}") from exc
    except URLError as exc:  # pragma: no cover - passthrough for runtime
        raise FetchError(f"Network error while fetching {url}: {exc.reason}") from exc


def fetch_text(url: str, *, headers: Dict[str, str] | None = None, timeout: int = 15, encoding: str = "utf-8") -> str:
    return fetch_bytes(url, headers=headers, timeout=timeout).decode(encoding, errors="replace")


def fetch_json(url: str, *, headers: Dict[str, str] | None = None, timeout: int = 15) -> Any:
    payload = fetch_text(url, headers=headers, timeout=timeout)
    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise FetchError(f"Failed to decode JSON from {url}") from exc


def polite_delay(seconds: float = 0.1) -> None:
    time.sleep(seconds)
