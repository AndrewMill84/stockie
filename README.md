# stockbot

Stockbot is a lightweight trading assistant that pulls market data, computes technical indicators, ranks tickers, and sends Telegram alerts when buy setups are detected. It is designed to run both locally (for development/testing) and unattended on a server (for daily scans and weekly decisions).

---

## What lives in this repo vs what lives on the server

### ✅ In this GitHub repository

* Application code (`stockbot/`)
* CLI entry points (`python -m stockbot ...`)
* Indicator + decision logic
* `requirements.txt`
* This README and supporting docs

### ⚠️ Not in the repo (must be created on each server)

* Python virtual environment (`venv/`)
* `.env` file (secrets + environment config)
* `data/` directory (state, portfolio, history)
* systemd service + timer files

These are **environment‑specific** and intentionally not committed.

---

## Quick start (local development)

```bash
python -m venv venv
source venv/bin/activate   # Windows: .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create a `.env` file in the project root (example below), then run:

```bash
python -m stockbot scan
```

---

## Common commands

Run a live scan (alerts only if a setup exists):

```bash
python -m stockbot scan
```

Send a forced Telegram test message:

```bash
python -m stockbot test-telegram
```

Toggle scan heartbeat notifications (from Telegram):

```
/log        # toggle on/off
/log on     # enable
/log off    # disable
```

Heartbeat messages are delivered at the end of each scan. The command is
processed the next time a scan runs.

Manually sync Telegram commands (without running a scan):

```bash
python -m stockbot telegram-sync
```

Listen for Telegram messages (long polling):

```bash
python -m stockbot telegram-listen
```

Replay historical signals:

```bash
python -m stockbot replay --days 180
```

Weekly ranking table:

```bash
python -m stockbot weekly-rank --top 3
```

---

## Environment configuration (.env)

Create `.env` in the project root:

```env
TICKERS=AAPL,MSFT,NVDA
LOOKBACK=6mo
INTERVAL=1d
MAX_ALERTS_PER_WEEK=1

STATE_FILE=/apt/stockie/data/state.json

# Telegram
TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_CHAT_ID=123456789
DRY_RUN=true

LOG_LEVEL=INFO
```

Notes:

* `DRY_RUN=true` logs messages instead of sending them.
* Use absolute paths for `STATE_FILE` in production.
* `data/` must exist and be writable.

---

## Production deployment (Proxmox / LXC / VM)

The recommended layout on a server is:

```
/apt/stockie
  ├── stockbot/
  ├── venv/
  ├── data/
  ├── .env
  └── requirements.txt
```

### 1. Install system packages

```bash
apt update
apt install -y python3 python3-venv python3-pip git
```

### 2. Clone the repo

```bash
cd /apt
git clone https://github.com/<your-user>/stockie.git
cd stockie
```

### 3. Create virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
mkdir -p data
```

### 4. Create `.env`

```bash
nano /apt/stockie/.env
```

(Add your configuration and Telegram credentials.)

### 5. Manual test

```bash
source venv/bin/activate
python -m stockbot scan
python -m stockbot test-telegram
```

---

## Running automatically with systemd

### Service file

Create:

```
/etc/systemd/system/stockbot.service
```

```ini
[Unit]
Description=Stockbot Scanner
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
WorkingDirectory=/apt/stockie
EnvironmentFile=/apt/stockie/.env
ExecStart=/apt/stockie/venv/bin/python -m stockbot scan
User=root
Group=root
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

Enable + test:

```bash
systemctl daemon-reload
systemctl start stockbot.service
journalctl -u stockbot.service -n 100 --no-pager
```

---

### Daily scheduler (timer)

Create:

```
/etc/systemd/system/stockbot.timer
```

```ini
[Unit]
Description=Run Stockbot daily

[Timer]
OnCalendar=*-*-* 08:30:00
Persistent=true
RandomizedDelaySec=300

[Install]
WantedBy=timers.target
```

Enable:

```bash
systemctl daemon-reload
systemctl enable --now stockbot.timer
systemctl list-timers | grep stockbot
```

Reboot test:

```bash
reboot
```

After reboot:

```bash
systemctl status stockbot.timer
```

---

## Where important files live on the server

* App code: `/apt/stockie`
* Secrets/config: `/apt/stockie/.env`
* State + history: `/apt/stockie/data/`
* Service unit: `/etc/systemd/system/stockbot.service`
* Scheduler: `/etc/systemd/system/stockbot.timer`
* Logs: `journalctl -u stockbot.service`

---

## Troubleshooting

View logs:

```bash
journalctl -u stockbot.service -n 200 --no-pager
```

Common issues:

* Wrong paths in `stockbot.service`
* `DRY_RUN=true` preventing Telegram sends
* Invalid Telegram token or chat id
* Missing `data/` directory

---

## How it works (high level)

* `stockbot/config.py` loads defaults and `.env` overrides.
* `stockbot/scanner.py` fetches data, computes indicators, and checks signals.
* `stockbot/signals.py` contains the buy‑signal rules.
* `stockbot/telegram.py` sends alerts using the Telegram Bot API.
* `stockbot/state.py` stores weekly alert counts to avoid spam.
