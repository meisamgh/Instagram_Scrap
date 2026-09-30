"""Backward-compatible wrapper for the correctly named get_followers.py script."""

from get_followers import main


if __name__ == "__main__":
    raise SystemExit(main())
