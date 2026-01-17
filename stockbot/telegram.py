"""Telegram messaging helper."""

import logging
import requests
from .config import Config

logger = logging.getLogger(__name__)


def send_telegram(text: str, cfg: Config) -> None:
    """Send a Telegram message unless dry-run is enabled."""
    if cfg.dry_run or not cfg.telegram_bot_token or not cfg.telegram_chat_id:
        logger.info("Telegram dry run or missing credentials. Message:\n%s", text)
        return

    # Telegram Bot API endpoint.
    url = f"https://api.telegram.org/bot{cfg.telegram_bot_token}/sendMessage"
    logger.info("Sending Telegram message to chat_id=%s", cfg.telegram_chat_id)
    r = requests.post(
        url, json={"chat_id": cfg.telegram_chat_id, "text": text, "parse_mode": "HTML"}
    )
    r.raise_for_status()


def fetch_telegram_updates(cfg: Config, offset: int | None = None) -> list:
    """Fetch incoming updates for the bot and return the raw update list."""
    if not cfg.telegram_bot_token:
        logger.info("Telegram bot token missing; cannot fetch updates.")
        return []

    url = f"https://api.telegram.org/bot{cfg.telegram_bot_token}/getUpdates"
    params = {"timeout": 10}
    if offset is not None:
        params["offset"] = offset

    r = requests.get(url, params=params)
    r.raise_for_status()
    data = r.json()
    return data.get("result", [])


def print_telegram_messages(cfg: Config, offset: int | None = None) -> int | None:
    """
    Fetch updates and print chat messages to console.
    Returns the next offset you can use to avoid duplicates.
    """
    updates = fetch_telegram_updates(cfg, offset=offset)
    if not updates:
        logger.info("No Telegram updates available.")
        return offset

    last_update_id = None
    for update in updates:
        last_update_id = update.get("update_id", last_update_id)
        msg = update.get("message") or update.get("edited_message") or {}
        chat = msg.get("chat", {})
        text = msg.get("text") or ""
        sender = msg.get("from", {}).get("username") or msg.get("from", {}).get("first_name", "")
        chat_id = chat.get("id", "")
        chat_title = chat.get("title") or chat.get("username") or ""
        if text:
            logger.info("Chat %s %s (%s): %s", chat_id, chat_title, sender, text)

    if last_update_id is None:
        return offset
    return last_update_id + 1


def _normalize_command(raw: str) -> tuple[str, list[str]] | None:
    """Parse a Telegram command like '/log on' into ('log', ['on'])."""
    if not raw or not raw.startswith("/"):
        return None
    cmd = raw.strip().split()
    if not cmd:
        return None
    head = cmd[0].lstrip("/").split("@", 1)[0].lower()
    args = [c.lower() for c in cmd[1:]]
    return head, args


def _command_to_bool(args: list[str], current: bool) -> bool:
    """Return new toggle state given command args; toggles if no args."""
    if not args:
        return not current
    if args[0] in {"on", "enable", "enabled", "true", "start", "yes"}:
        return True
    if args[0] in {"off", "disable", "disabled", "false", "stop", "no"}:
        return False
    return not current


def process_telegram_commands(cfg: Config, state: dict) -> dict:
    """
    Look for bot commands and update state.
    Supported commands: /log, /log on, /log off (also /heartbeat, /hb).
    """
    telegram_state = state.setdefault("telegram", {})
    telegram_state.setdefault("heartbeat_enabled", False)
    telegram_state.setdefault("last_update_id", None)

    if not cfg.telegram_bot_token:
        logger.info("Telegram bot token missing; skipping command sync.")
        return state

    offset = telegram_state.get("last_update_id")
    if offset is not None:
        offset = offset + 1

    updates = fetch_telegram_updates(cfg, offset=offset)
    if not updates:
        return state

    last_update_id = telegram_state.get("last_update_id")
    for update in updates:
        update_id = update.get("update_id")
        if update_id is not None:
            last_update_id = update_id
        msg = update.get("message") or update.get("edited_message") or {}
        text = msg.get("text") or ""
        chat = msg.get("chat") or {}
        chat_id = chat.get("id")
        if cfg.telegram_chat_id and str(chat_id) != str(cfg.telegram_chat_id):
            continue

        parsed = _normalize_command(text)
        if not parsed:
            continue
        cmd, args = parsed
        if cmd not in {"log", "heartbeat", "hb"}:
            continue

        current = bool(telegram_state.get("heartbeat_enabled", False))
        new_value = _command_to_bool(args, current)
        telegram_state["heartbeat_enabled"] = new_value
        status = "enabled" if new_value else "disabled"
        send_telegram(f"Heartbeat notifications {status}.", cfg)
        logger.info("Telegram heartbeat toggled: %s", status)

    telegram_state["last_update_id"] = last_update_id
    return state