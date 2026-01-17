"""Weekly ranking of tickers based on a simple scoring model."""

import datetime as dt
import pandas as pd

from .config import Config
from .decision_engine import DecisionEngine
from .data_sources.yahoo import fetch_data
from .indicators import compute_indicators
from .setups import add_setup_type
from .telegram import send_telegram


def compute_indicators_plus(df: pd.DataFrame) -> pd.DataFrame:
    """Compute base indicators plus momentum, ATR, and volatility."""
    df = compute_indicators(df)

    # 5-day momentum (percent change).
    df["MOM5"] = df["Close"].pct_change(5)

    # ATR(14): average true range for volatility.
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    tr = pd.concat(
        [
            (high - low),
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)
    df["ATR14"] = tr.rolling(14).mean()

    # 20-day realized volatility of returns.
    df["VOLAT20"] = df["Close"].pct_change().rolling(20).std()

    return df


def score_setup(latest: dict) -> dict:
    """Compute a simple score breakdown and total score for ranking."""
    rsi = latest["rsi14"]
    mom5 = latest["mom5"]
    vol = latest["volat20"]
    close = latest["close"]
    sma50 = latest["sma50"]

    # Distance to SMA50 (positive = above).
    dist_sma50_pct = (close - sma50) / sma50 if sma50 else 0.0

    # Heuristic scoring components (0..1-ish).
    rsi_score = 1.0 - min(abs(rsi - 50) / 50.0, 1.0)
    mom_score = max(min(mom5 * 5.0, 1.0), -1.0)
    vol_score = 1.0 - min(vol * 10.0, 1.0) if vol is not None else 0.0
    dist_score = 1.0 - min(abs(dist_sma50_pct) * 5.0, 1.0)

    final_score = (0.35 * rsi_score) + (0.30 * mom_score) + (0.20 * vol_score) + (
        0.15 * dist_score
    )

    return {
        "dist_sma50_pct": dist_sma50_pct,
        "rsi_score": rsi_score,
        "mom_score": mom_score,
        "vol_score": vol_score,
        "dist_score": dist_score,
        "final_score": final_score,
    }


def rank_best_setups_this_week(
    cfg: Config, top_n: int = 3, send: bool = True
) -> pd.DataFrame:
    """
    Score each ticker using the latest available day and return a ranked table.
    Optionally send a Telegram message with the top N.
    """
    rows = []

    for t in cfg.tickers:
        df = fetch_data(t, cfg)
        if df.empty:
            continue

        df = compute_indicators_plus(df).dropna()
        if df.empty or len(df) < 60:
            continue

        last = df.iloc[-1]

        latest = {
            "ticker": t,
            "date": str(last.name.date()),
            "close": float(last["Close"]),
            "sma20": float(last["SMA20"]),
            "sma50": float(last["SMA50"]),
            "rsi14": float(last["RSI14"]),
            "mom5": float(last["MOM5"]),
            "atr14": float(last["ATR14"]),
            "volat20": float(last["VOLAT20"]),
        }

        breakdown = score_setup(latest)
        rows.append({**latest, **breakdown})

    if not rows:
        ranked = pd.DataFrame()
    else:
        ranked = (
            pd.DataFrame(rows)
            .sort_values("final_score", ascending=False)
            .reset_index(drop=True)
        )
    ranked = add_setup_type(ranked)

    decision_engine = DecisionEngine()
    decision = decision_engine.make_weekly_decision(ranked, cfg, top_n=top_n)

    if send:
        today = dt.date.today().strftime("%Y-%m-%d")
        medals = ["🥇", "🥈", "🥉"]
        lines = [f"<b>TOP {min(top_n, len(ranked))} SETUPS (as of {today})</b>"]

        if ranked.empty:
            lines.append("\nNo valid data / not enough history for scoring.")
        else:
            for i in range(min(top_n, len(ranked))):
                r = ranked.iloc[i]
                medal = medals[i] if i < 3 else f"{i + 1}."
                lines.append(
                    f"\n{medal} <b>{r['ticker']}</b> ({r['date']})"
                    f"\nScore: {r['final_score']:.3f}"
                    f"\nClose: {r['close']:.2f}"
                    f"\nRSI14: {r['rsi14']:.1f} | MOM5: {r['mom5']*100:.2f}%"
                    f"\nDist→SMA50: {r['dist_sma50_pct']*100:.2f}% | "
                    f"Vol(20d): {r['volat20']*100:.2f}%"
                f"\nSetup: {r['setup_type']}"
                )

        lines.append("\n<b>WEEKLY DECISION</b>")
        if decision["action"] == "BUY":
            lines.append(
                f"Action: BUY {decision['ticker']} ({decision['setup_type']})"
            )
            lines.append(f"Position: {decision['position_sizing']}")
            lines.append(
                f"Entry: {decision['entry_logic']['type']} — "
                f"{decision['entry_logic']['logic']}"
            )
            lines.append(
                f"Risk: {decision['risk_logic']['invalidation']} | "
                f"Stop: {decision['risk_logic']['stop']}"
            )
            lines.append(f"Reasoning: {decision['reasoning']}")
        elif decision["action"] == "HOLD":
            lines.append("Action: HOLD (already decided this week)")
            lines.append(f"Reason: {decision['reason']}")
        else:
            lines.append("Action: SKIP (no eligible picks)")
            lines.append(f"Reason: {decision['reason']}")

        send_telegram("\n".join(lines), cfg)

    ranked.attrs["decision"] = decision
    return ranked
