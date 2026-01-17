"""Persisted state for weekly alert throttling."""

import datetime as dt
import json
import logging
from pathlib import Path
from .config import Config

logger = logging.getLogger(__name__)


def load_state(cfg: Config):
    """Load the JSON state file if it exists, otherwise return defaults."""
    path = Path(cfg.state_file)
    if not path.exists():
        logger.info("State file not found, starting fresh: %s", path)
        return {"weekly_alert_counts_by_ticker": {}}
    logger.info("Loading state: %s", path)
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state, cfg: Config):
    """Write the state file to disk, creating the folder if needed."""
    path = Path(cfg.state_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Saving state: %s", path)
    with path.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def iso_week_key(d: dt.date) -> str:
    """Convert a date to an ISO year-week key like '2026-03'."""
    y, w, _ = d.isocalendar()
    return f"{y}-{w:02d}"


def can_send_weekly_alert_for_ticker(state, ticker: str) -> bool:
    """True if this ticker has not alerted yet this week."""
    week = iso_week_key(dt.date.today())
    bucket = state.get("weekly_alert_counts_by_ticker", {})
    week_map = bucket.get(week, {})
    return week_map.get(ticker, 0) < 1


def increment_weekly_alert_for_ticker(state, ticker: str):
    """Increment the per-ticker weekly alert count in state."""
    week = iso_week_key(dt.date.today())
    state.setdefault("weekly_alert_counts_by_ticker", {})
    state["weekly_alert_counts_by_ticker"].setdefault(week, {})
    state["weekly_alert_counts_by_ticker"][week][ticker] = (
        state["weekly_alert_counts_by_ticker"][week].get(ticker, 0) + 1
    )