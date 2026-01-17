# Project Detail — Stockbot

## What This Project Is
Stockbot is a lightweight trading assistant that pulls market data, computes
technical indicators, ranks tickers, and produces a single weekly decision
based on deterministic rules. It can send Telegram summaries and it persists
state so decisions are consistent week to week.

## Current Capabilities
- Download price/volume data (Yahoo Finance).
- Compute indicators (SMA20/50, RSI14, MOM5, ATR14, VOLAT20).
- Rank tickers by a scoring model and print a ranked table.
- Classify each ranked ticker into a setup type.
- Produce one weekly BUY/HOLD/SKIP decision with entry/stop logic.
- Persist decisions to `data/state.json` and holdings to `data/portfolio.json`.
- Send Telegram summaries (or dry-run to console).

## What We’ve Implemented So Far
- **Weekly ranking output** prints a DataFrame and a decision JSON in the CLI.
- **Setup classification** rules:
  - REVERSION: RSI14 ≤ 20 and dist to SMA50 ≤ −4%
  - TREND_RESET: 25 ≤ RSI14 ≤ 45 and |dist to SMA50| ≤ 2%
  - MOMENTUM: MOM5 > 0 and dist to SMA50 > 0
  - else UNKNOWN
- **Decision engine**:
  - Enforces once‑per‑week logic and avoids re‑buying open holdings.
  - Filters candidates by MIN_SCORE_TO_BUY and ALLOW_SETUP_TYPES.
  - Uses tie‑breakers when scores are within a small epsilon.
  - Derives position sizing, entry type, and risk logic from setup type.
  - Saves decision + portfolio updates.
- **Config knobs** (via `.env` or defaults):
  - `MIN_SCORE_TO_BUY`
  - `MAX_ALERTS_PER_WEEK`
  - `ALLOW_SETUP_TYPES`

## How the Analysis Works (Plain English)
1) **Data fetch**: For each ticker, we download recent prices and volume.
2) **Indicators**: We calculate trend (SMA20/50), momentum (MOM5), and risk
   measures (RSI14, ATR14, VOLAT20).
3) **Scoring**: Each ticker gets a score that blends RSI, momentum, volatility,
   and distance from the SMA50.
4) **Setup classification**: Each ranked ticker is tagged as REVERSION,
   TREND_RESET, MOMENTUM, or UNKNOWN based on deterministic thresholds.
5) **Eligibility filters**: We only consider candidates that pass minimum score,
   allowed setup types, weekly buy limits, and “not already held”.
6) **Tie‑breakers**: If top scores are very close, we apply setup‑specific
   logic (e.g., lower RSI wins for REVERSION).
7) **Decision**: We emit one BUY/HOLD/SKIP decision with sizing, entry, and
   risk logic, then persist it to disk.

## Where Key Logic Lives
- `stockbot/weekly_rank.py`: ranking + weekly decision + Telegram summary
- `stockbot/decision_engine.py`: eligibility + tie‑breakers + decision output
- `stockbot/setups.py`: setup classification rules
- `stockbot/indicators.py`: SMA/RSI/volume indicators
- `stockbot/state.py`: weekly decision state
- `stockbot/portfolio.py`: holdings persistence

## How to Run
```
# Weekly decision (prints ranked table + decision)
python -m stockbot weekly-rank --top 10 --no-send

# Run all sanity tests (PowerShell)
.\tests.ps1
```
