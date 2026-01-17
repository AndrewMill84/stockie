# stockbot

Stockbot downloads price data, computes indicators, and sends Telegram alerts
when a buy setup is detected.

## Quick start

1) Create a virtual environment and install dependencies:

```
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2) Create a `.env` file (optional but recommended).

## Commands

Run a live scan and send Telegram alerts (if configured):

```
python -m stockbot scan
```

Replay historical signals for the last N days:

```
python -m stockbot replay --days 180
```

Send a test Telegram message:

```
python -m stockbot test-telegram
```

Run the basic sanity test suite:

```
# Windows PowerShell
.\tests.ps1
```

Rank tickers for the week (optionally send Telegram summary):

```
python -m stockbot weekly-rank --top 3
```

Note: The command prints a ranked DataFrame to the console.

Fetch recent Telegram messages for the bot and print them:

```
python -m stockbot get-telegram
```

Note: The command prints a `Next offset` value. Use it to avoid duplicates:

```
python -m stockbot get-telegram --offset <next_offset>
```

## Environment variables

Create a `.env` file in the project root with any of these:

```
TICKERS=AAPL,MSFT,NVDA
LOOKBACK=6mo
INTERVAL=1d
MAX_ALERTS_PER_WEEK=1
STATE_FILE=data/state.json

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
DRY_RUN=true

# Logging
LOG_LEVEL=INFO
```

Notes:
- If `DRY_RUN=true`, Telegram messages are logged to the console instead of sent.
- If `STATE_FILE` doesn't exist, it will be created on first run.

## How it works (high level)

- `stockbot/config.py` loads defaults and `.env` overrides.
- `stockbot/scanner.py` fetches data, computes indicators, and checks signals.
- `stockbot/signals.py` contains the buy‑signal rules.
- `stockbot/telegram.py` sends alerts using the Telegram Bot API.
- `stockbot/state.py` stores weekly alert counts to avoid spam.

## Troubleshooting

- If Telegram messages are not sent, verify `DRY_RUN=false` and your bot token
  + chat ID are correct.
- Set `LOG_LEVEL=DEBUG` to see more console output.