# Proxmox Operations Manual — Stockbot + Django Stack

This document is the day‑to‑day run‑book for the Proxmox container (CT100) running:

* Docker
* Django stack (`mysite`)
* Stockbot trading bot

It covers how the system boots, where things live, and the exact commands used to operate, debug, and update the platform.

---

# 🧠 System Architecture Overview

On container boot, the system starts in this order:

OS → Docker → Django Docker stack → Stockbot timer → Stockbot service (daily)

Controlled by systemd:

* `docker.service`
* `mysite.service` (runs `docker compose up -d`)
* `stockbot.timer` (daily scheduler)
* `stockbot.service` (runs the trading scan)

---

# 📁 Important Locations

### Django project

```
/root/github/mysite/
```

Contains `docker-compose.yml` and Django application code.

### Stockbot project

```
/apt/stockie/
```

Contains the Stockbot application and virtual environment.

### Stockbot runtime files (not in GitHub)

```
/apt/stockie/.env
/apt/stockie/data/state.json
```

### System services (not in GitHub)

```
/etc/systemd/system/mysite.service
/etc/systemd/system/stockbot.service
/etc/systemd/system/stockbot.timer
```

---

# 🖥️ System & Service Status

Check core services:

```bash
systemctl status docker --no-pager
systemctl status mysite.service --no-pager
systemctl status stockbot.service --no-pager
systemctl status stockbot.timer --no-pager
```

View boot/system errors:

```bash
journalctl -xb --no-pager
```

Reboot container:

```bash
reboot
```

---

# 🐳 Django / Docker Operations

Always run inside:

```bash
cd /root/github/mysite
```

Start stack:

```bash
docker compose up -d --build
```

Stop stack:

```bash
docker compose down
```

Restart stack:

```bash
docker compose restart
```

View running containers:

```bash
docker compose ps
```

View logs:

```bash
docker compose logs -f
```

Enter Django container (replace `web` if different):

```bash
docker compose exec web bash
```

Django management:

```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py collectstatic
```

---

# 🤖 Stockbot Operations

Go to Stockbot folder:

```bash
cd /apt/stockie
source venv/bin/activate
```

Manual scan:

```bash
python -m stockbot scan
```

Weekly ranking:

```bash
python -m stockbot weekly-rank --top 5
```

Test Telegram:

```bash
python -m stockbot test-telegram
```

Run via systemd (production mode):

```bash
systemctl start stockbot.service
```

View Stockbot logs:

```bash
journalctl -u stockbot.service -n 100 --no-pager
```

Check next scheduled run:

```bash
systemctl list-timers | grep stockbot
```

---

# ⚙️ systemd Management

Reload after editing services:

```bash
systemctl daemon-reload
```

Restart Django service:

```bash
systemctl restart mysite.service
```

Restart Stockbot service:

```bash
systemctl restart stockbot.service
```

Enable / disable services:

```bash
systemctl enable mysite.service
systemctl disable mysite.service

systemctl enable stockbot.timer
systemctl disable stockbot.timer
```

---

# 🔄 Update Workflows

### Update Stockbot

```bash
cd /apt/stockie
git pull
systemctl start stockbot.service
```

### Update Django app

```bash
cd /root/github/mysite
git pull
docker compose up -d --build
```

---

# 🧩 Mental Model

* Docker keeps Django alive
* systemd keeps Docker + Django alive
* systemd timer schedules Stockbot
* Stockbot persists memory in `data/state.json`
* GitHub stores code only (never secrets or runtime state)

---

# 🚨 First Response Checklist

If something breaks:

```bash
systemctl status docker
systemctl status mysite.service
systemctl status stockbot.timer
journalctl -u stockbot.service -n 100 --no-pager
```

---

# 🥇 Notes

* `mysite.service` is a oneshot service — it will show `active (exited)` when healthy.
* `stockbot.service` is a oneshot service — it runs, then exits.
* Only `stockbot.timer` stays permanently active.

---

Last updated: 2026‑01‑17
