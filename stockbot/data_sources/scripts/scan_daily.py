"""Simple script entrypoint for running a daily scan."""

from stockbot.config import Config
from stockbot.scanner import run_scan

if __name__ == "__main__":
    # Load config from .env/environment and run the scan.
    cfg = Config.from_env()
    run_scan(cfg)