"""Portfolio persistence helpers."""

import json
import logging
from pathlib import Path

from .config import Config

logger = logging.getLogger(__name__)


def load_portfolio(cfg: Config) -> dict:
    """Load portfolio JSON or return defaults."""
    path = Path(cfg.portfolio_file)
    if not path.exists():
        logger.info("Portfolio file not found, starting fresh: %s", path)
        return {"holdings": [], "history": []}
    logger.info("Loading portfolio: %s", path)
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_portfolio(portfolio: dict, cfg: Config) -> None:
    """Write the portfolio file to disk, creating the folder if needed."""
    path = Path(cfg.portfolio_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Saving portfolio: %s", path)
    with path.open("w", encoding="utf-8") as f:
        json.dump(portfolio, f, indent=2)
