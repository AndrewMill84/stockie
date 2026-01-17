"""Technical indicators used for signal generation."""

import pandas as pd


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add rolling indicators (SMA, RSI, volume) to a price DataFrame."""
    df = df.copy()
    # Simple moving averages.
    df["SMA20"] = df["Close"].rolling(20).mean()
    df["SMA50"] = df["Close"].rolling(50).mean()

    # RSI(14) calculation.
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / (loss.replace(0, 1e-9))
    df["RSI14"] = 100 - (100 / (1 + rs))

    # Average volume for confirmation.
    df["VOL20"] = df["Volume"].rolling(20).mean()
    return df