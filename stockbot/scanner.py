"""Run a live scan across tickers and send Telegram alerts."""

import logging
from .config import Config
from .data_sources.yahoo import fetch_data
from .indicators import compute_indicators
from .signals import buy_signal
from .state import (
    load_state,
    save_state,
    can_send_weekly_alert_for_ticker,
    increment_weekly_alert_for_ticker,
)
from .telegram import send_telegram, process_telegram_commands

logger = logging.getLogger(__name__)


def run_scan(cfg: Config):
    """Scan all configured tickers and send a Telegram alert if any signal fires."""
    logger.info(
        "Starting scan (tickers=%s, lookback=%s, interval=%s)",
        ",".join(cfg.tickers),
        cfg.lookback,
        cfg.interval,
    )
    # Load state so we can throttle alerts (per ticker, per week).
    state = load_state(cfg)
    # Process inbound Telegram commands (e.g., /log on/off).
    state = process_telegram_commands(cfg, state)
    # Collect any signals we find so we can send one combined message.
    alerts = []

    for t in cfg.tickers:
        # Skip tickers that already alerted this week.
        if not can_send_weekly_alert_for_ticker(state, t):
            logger.info("%s: already alerted this week — skipping.", t)
            continue

        # Download price/volume history.
        logger.info("%s: fetching data", t)
        df = fetch_data(t, cfg)
        if df.empty:
            logger.warning("%s: no data returned", t)
            continue

        # Add indicators (SMA, RSI, volume averages) and evaluate the signal.
        df = compute_indicators(df)
        sig = buy_signal(df)
        if sig:
            logger.info("%s: signal detected for %s", t, sig["date"])
            alerts.append((t, sig))

    if alerts:
        # Build a single Telegram message that contains all tickers with signals.
        lines = ["<b>BUY SETUPS FOUND</b>"]
        for t, sig in alerts:
            lines.append(
                f"\n<b>{t}</b> ({sig['date']})"
                f"\nClose: {sig['close']:.2f}"
                f"\nSMA20/SMA50: {sig['sma20']:.2f} / {sig['sma50']:.2f}"
                f"\nRSI14: {sig['rsi14']:.1f}"
                f"\nVol: {sig['volume']} (avg20: {sig['vol20']:.0f})"
            )
            # Mark this ticker as alerted so it won't spam in the same week.
            increment_weekly_alert_for_ticker(state, t)

        message = "\n".join(lines)
        logger.info("Sending alert to Telegram (%d tickers)", len(alerts))
        send_telegram(message, cfg)
    else:
        # Nothing matched the signal rules today.
        logger.info("No buy setups today.")

    if state.get("telegram", {}).get("heartbeat_enabled"):
        summary = (
            f"Scan complete: {len(cfg.tickers)} tickers, "
            f"{len(alerts)} alert(s) found."
        )
        send_telegram(summary, cfg)

    # Persist state after scan (alerts, command sync, heartbeat).
    save_state(state, cfg)

    return {"alerts": alerts, "state": state}