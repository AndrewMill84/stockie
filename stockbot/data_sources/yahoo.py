"""Yahoo Finance data source wrapper."""

import logging
import pandas as pd
import yfinance as yf
from ..config import Config

logger = logging.getLogger(__name__)


def normalize_yf_df(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """Flatten yfinance output to a simple single-level column DataFrame."""
    if isinstance(df.columns, pd.MultiIndex):
        if ticker in df.columns.get_level_values(-1):
            df = df.xs(ticker, axis=1, level=-1, drop_level=True)
        else:
            df.columns = [c[0] for c in df.columns]
    return df


def fetch_data(ticker: str, cfg: Config) -> pd.DataFrame:
    """Download OHLCV data for a ticker and normalize the output format."""
    logger.info("Downloading %s (period=%s, interval=%s)", ticker, cfg.lookback, cfg.interval)
    df = yf.download(
        ticker, period=cfg.lookback, interval=cfg.interval, auto_adjust=True, progress=False
    )
    if df is None or df.empty:
        logger.warning("%s: empty response from data source", ticker)
        return pd.DataFrame()
    return normalize_yf_df(df, ticker)