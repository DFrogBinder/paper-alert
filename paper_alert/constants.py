from __future__ import annotations

import os
from datetime import timedelta

DEFAULT_KEYWORDS = (
    "temporal interference",
    "temporal interference stimulation",
    "ti stimulation",
)

MAX_RESULTS_PER_SOURCE = 25
TRIAGE_STATES = ("new", "saved", "dismissed", "later")
DEFAULT_TRIAGE_STATE = "new"

BIORXIV_LOOKBACK = timedelta(days=30)

DEFAULT_USER_AGENT = "PaperAlert/1.0 (contact: change-me@example.com)"


def get_user_agent() -> str:
    return os.getenv("PAPER_ALERT_USER_AGENT", DEFAULT_USER_AGENT)
