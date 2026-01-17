"""Package entrypoint so `python -m stockbot ...` runs the CLI."""

from .cli import main

if __name__ == "__main__":
    # Hand off to the command-line interface.
    main()