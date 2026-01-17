"""Signal rules for deciding whether a buy setup exists."""

import pandas as pd


def buy_signal(df: pd.DataFrame) -> dict | None:
    """Return a signal dict if rules are met, otherwise None."""
    if len(df) < 60:
        return None

    # Remove rows with NaN indicators before checking rules.
    df = df.dropna()
    if len(df) < 2:
        return None

    # Compare the last two rows for a "reclaim SMA20" condition.
    last = df.iloc[-1]
    prev = df.iloc[-2]

    # Rule set: reclaim SMA20 + trend up + RSI below 65 + volume confirmation.
    reclaim_sma20 = (prev["Close"].item() < prev["SMA20"].item()) and (
        last["Close"].item() > last["SMA20"].item()
    )
    trend_ok = last["SMA20"].item() > last["SMA50"].item()
    rsi_ok = last["RSI14"].item() < 65
    vol_ok = last["Volume"].item() > last["VOL20"].item()

    if reclaim_sma20 and trend_ok and rsi_ok and vol_ok:
        # Return a compact summary used in Telegram alerts.
        return {
            "date": str(last.name.date()),
            "close": float(last["Close"].item()),
            "sma20": float(last["SMA20"].item()),
            "sma50": float(last["SMA50"].item()),
            "rsi14": float(last["RSI14"].item()),
            "volume": int(last["Volume"].item()),
            "vol20": float(last["VOL20"].item()),
        }
    return None