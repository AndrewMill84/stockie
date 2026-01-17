"""Replay past data to see when signals would have triggered."""

import pandas as pd
from .config import Config
from .data_sources.yahoo import fetch_data
from .indicators import compute_indicators
from .signals import buy_signal


def replay_signals(ticker: str, cfg: Config, max_days: int = 180) -> pd.DataFrame:
    """Scan backwards in time and return a DataFrame of historical signals."""
    df = fetch_data(ticker, cfg)
    if df.empty:
        return pd.DataFrame()

    # Compute indicators once, then test signals on rolling slices.
    df = compute_indicators(df)
    signals = []

    # Only start once we have enough rows for indicators.
    start = max(60, len(df) - max_days)
    for i in range(start, len(df)):
        # Evaluate the signal as if we only knew data up to this point.
        subset_df = df.iloc[: i + 1]
        sig = buy_signal(subset_df)
        if sig:
            signals.append({"ticker": ticker, **sig})

    return pd.DataFrame(signals)