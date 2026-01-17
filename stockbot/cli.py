"""Command-line interface for running scans, replays, and Telegram tests."""

import argparse
import json
import pandas as pd
from .config import Config, setup_logging
from .scanner import run_scan
from .replay import replay_signals
from .telegram import (
    listen_for_telegram_messages,
    print_telegram_messages,
    process_telegram_commands,
    send_telegram,
)
from .weekly_rank import rank_best_setups_this_week
from .state import load_state, save_state


def build_cfg_from_args(args) -> Config:
    # Start from environment/.env defaults.
    cfg = Config.from_env()

    # Override defaults with CLI flags if they were provided.
    if getattr(args, "tickers", None):
        cfg.tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    if getattr(args, "lookback", None):
        cfg.lookback = args.lookback
    if getattr(args, "interval", None):
        cfg.interval = args.interval
    if getattr(args, "state_file", None):
        cfg.state_file = args.state_file
    if getattr(args, "max_alerts_per_week", None) is not None:
        cfg.max_buy_alerts_per_week = args.max_alerts_per_week
    if getattr(args, "telegram_bot_token", None):
        cfg.telegram_bot_token = args.telegram_bot_token
    if getattr(args, "telegram_chat_id", None):
        cfg.telegram_chat_id = args.telegram_chat_id
    if getattr(args, "dry_run", None):
        cfg.dry_run = True

    return cfg


def main():
    # Enable console logging early.
    setup_logging()
    p = argparse.ArgumentParser(description="Stockbot CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    # Scan command: live scan that can send Telegram alerts.
    scan = sub.add_parser("scan")
    scan.add_argument("--tickers")
    scan.add_argument("--lookback")
    scan.add_argument("--interval")
    scan.add_argument("--state-file")
    scan.add_argument("--max-alerts-per-week", type=int)
    scan.add_argument("--telegram-bot-token")
    scan.add_argument("--telegram-chat-id")
    scan.add_argument("--dry-run", action="store_true")

    # Replay command: backtest signals over a window of days.
    replay = sub.add_parser("replay")
    replay.add_argument("--tickers")
    replay.add_argument("--lookback")
    replay.add_argument("--interval")
    replay.add_argument("--days", type=int, default=180)

    # Test command: send a simple Telegram message.
    test = sub.add_parser("test-telegram")
    test.add_argument("--message", default="Stockbot test message")
    test.add_argument("--dry-run", action="store_true")

    # Fetch command: print recent Telegram messages for this bot.
    fetch = sub.add_parser("get-telegram")
    fetch.add_argument("--offset", type=int)

    # Sync command: process inbound Telegram commands (e.g., /log on/off).
    sync = sub.add_parser("telegram-sync")
    sync.add_argument("--state-file")

    # Listen command: long-poll Telegram and log messages/commands.
    listen = sub.add_parser("telegram-listen")
    listen.add_argument("--state-file")
    listen.add_argument("--poll-seconds", type=float, default=1.0)
    listen.add_argument("--no-log-messages", action="store_true")

    # Weekly rank command: score and rank tickers for the week.
    weekly = sub.add_parser("weekly-rank")
    weekly.add_argument("--top", type=int, default=3)
    weekly.add_argument("--no-send", action="store_true")

    args = p.parse_args()
    cfg = build_cfg_from_args(args)

    if args.cmd == "scan":
        run_scan(cfg)
    elif args.cmd == "replay":
        # Combine any ticker results into a single table.
        all_hits = []
        for t in cfg.tickers:
            df_hits = replay_signals(t, cfg, max_days=args.days)
            if not df_hits.empty:
                all_hits.append(df_hits)
        summary = pd.concat(all_hits, ignore_index=True) if all_hits else pd.DataFrame()
        print(summary)
    elif args.cmd == "test-telegram":
        if args.dry_run:
            cfg.dry_run = True
        send_telegram(args.message, cfg)
    elif args.cmd == "weekly-rank":
        ranked = rank_best_setups_this_week(cfg, top_n=args.top, send=not args.no_send)
        print(ranked)
        decision = ranked.attrs.get("decision")
        if decision:
            print("\nDecision:")
            print(json.dumps(decision, indent=2))
    elif args.cmd == "get-telegram":
        next_offset = print_telegram_messages(cfg, offset=args.offset)
        if next_offset is not None:
            print(f"Next offset: {next_offset}")
    elif args.cmd == "telegram-sync":
        state = load_state(cfg)
        state = process_telegram_commands(cfg, state)
        save_state(state, cfg)
    elif args.cmd == "telegram-listen":
        state = load_state(cfg)
        listen_for_telegram_messages(
            cfg,
            state,
            poll_seconds=args.poll_seconds,
            log_messages=not args.no_log_messages,
            on_state_update=lambda s: save_state(s, cfg),
        )