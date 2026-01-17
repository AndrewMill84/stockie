"""Configuration helpers for stockbot (env/.env + defaults)."""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    # Optional dependency: only used to load values from .env
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STATE_FILE = PROJECT_ROOT / "data" / "state.json"
DEFAULT_PORTFOLIO_FILE = PROJECT_ROOT / "data" / "portfolio.json"

DEFAULT_TICKERS = ["AAPL", "MSFT", "NVDA"]
DEFAULT_LOOKBACK = "6mo"
DEFAULT_INTERVAL = "1d"
DEFAULT_MAX_ALERTS_PER_WEEK = 1
DEFAULT_MIN_SCORE_TO_BUY = 0.62
DEFAULT_ALLOW_SETUP_TYPES = ["REVERSION", "TREND_RESET", "MOMENTUM"]


@dataclass
class Config:
    """Runtime settings used across the app."""

    tickers: list
    lookback: str = DEFAULT_LOOKBACK
    interval: str = DEFAULT_INTERVAL
    max_buy_alerts_per_week: int = DEFAULT_MAX_ALERTS_PER_WEEK
    min_score_to_buy: float = DEFAULT_MIN_SCORE_TO_BUY
    allow_setup_types: list = field(default_factory=lambda: DEFAULT_ALLOW_SETUP_TYPES.copy())
    state_file: str = str(DEFAULT_STATE_FILE)
    portfolio_file: str = str(DEFAULT_PORTFOLIO_FILE)
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    dry_run: bool = True

    @classmethod
    def from_env(cls) -> "Config":
        """Load config from .env/environment and fall back to defaults."""
        if load_dotenv:
            load_dotenv()

        # Tickers list can be overridden with a comma-separated string.
        tickers_raw = os.getenv("TICKERS")
        if tickers_raw:
            tickers = [t.strip().upper() for t in tickers_raw.split(",") if t.strip()]
        else:
            tickers = DEFAULT_TICKERS.copy()

        # DRY_RUN=true means no live Telegram sends.
        dry_run_raw = os.getenv("DRY_RUN", "true").lower().strip()
        dry_run = dry_run_raw in {"1", "true", "yes", "y"}

        # Optional allow-list for setup types.
        allow_raw = os.getenv("ALLOW_SETUP_TYPES")
        if allow_raw:
            allow_setup_types = [s.strip().upper() for s in allow_raw.split(",") if s.strip()]
        else:
            allow_setup_types = DEFAULT_ALLOW_SETUP_TYPES.copy()

        return cls(
            tickers=tickers,
            lookback=os.getenv("LOOKBACK", DEFAULT_LOOKBACK),
            interval=os.getenv("INTERVAL", DEFAULT_INTERVAL),
            max_buy_alerts_per_week=int(
                os.getenv("MAX_ALERTS_PER_WEEK", str(DEFAULT_MAX_ALERTS_PER_WEEK))
            ),
            min_score_to_buy=float(
                os.getenv("MIN_SCORE_TO_BUY", str(DEFAULT_MIN_SCORE_TO_BUY))
            ),
            allow_setup_types=allow_setup_types,
            state_file=os.getenv("STATE_FILE", str(DEFAULT_STATE_FILE)),
            portfolio_file=os.getenv("PORTFOLIO_FILE", str(DEFAULT_PORTFOLIO_FILE)),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN") or None,
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID") or None,
            dry_run=dry_run,
        )


def setup_logging() -> None:
    """Configure standard console logging for the app."""
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )