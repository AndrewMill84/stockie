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