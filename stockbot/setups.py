"""Setup classification helpers (pure + deterministic)."""

from __future__ import annotations

from enum import Enum
import pandas as pd


class SetupType(str, Enum):
    REVERSION = "REVERSION"
    TREND_RESET = "TREND_RESET"
    MOMENTUM = "MOMENTUM"
    UNKNOWN = "UNKNOWN"


def classify_setup(row: dict) -> str:
    """
    Classify a single row into a setup type.
    Rules (MVP):
    - REVERSION: RSI14 <= 20 AND dist_sma50_pct <= -4
    - TREND_RESET: 25 <= RSI14 <= 45 AND abs(dist_sma50_pct) <= 2
    - MOMENTUM: MOM5 > 0 AND dist_sma50_pct > 0
    - else UNKNOWN
    """
    rsi14 = float(row.get("rsi14", 0.0))
    dist_sma50 = float(row.get("dist_sma50_pct", 0.0))
    mom5 = float(row.get("mom5", 0.0))

    if rsi14 <= 20 and dist_sma50 <= -4:
        return SetupType.REVERSION.value
    if 25 <= rsi14 <= 45 and abs(dist_sma50) <= 2:
        return SetupType.TREND_RESET.value
    if mom5 > 0 and dist_sma50 > 0:
        return SetupType.MOMENTUM.value
    return SetupType.UNKNOWN.value


def add_setup_type(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with setup_type column added."""
    df = df.copy()
    df["setup_type"] = df.apply(lambda r: classify_setup(r.to_dict()), axis=1)
    return df
