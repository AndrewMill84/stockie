$ErrorActionPreference = "Stop"

python -m stockbot test-telegram --dry-run
python -m stockbot weekly-rank --top 10 --no-send
python -m stockbot scan --dry-run
python -m stockbot replay --days 30
