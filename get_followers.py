"""Collect follower metadata for a public Instagram account.

Credentials are loaded from environment variables; see .env.example.
"""

from __future__ import annotations

import argparse
import logging
import os
import time
from typing import Any

import pandas as pd

from scraper_runtime import (
    atomic_write_csv,
    build_clients,
    choose_client,
    configure_logging,
    load_csv,
    load_json,
    output_directory,
    retry_call,
    save_json,
)

LOGGER = logging.getLogger("followers")


def accounts_to_frame(accounts: list[Any]) -> pd.DataFrame:
    rows = [dict(vars(account)) for account in accounts]
    frame = pd.DataFrame(rows)
    if "identifier" in frame.columns:
        frame = frame.rename(columns={"identifier": "user_ID"})
    return frame


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect Instagram followers")
    parser.add_argument("page_name", help="Target public Instagram username")
    parser.add_argument("--output-dir", default=os.getenv("OUTPUT_PATH", "./data"))
    parser.add_argument("--page-size", type=int, default=50)
    parser.add_argument("--request-attempts", type=int, default=4)
    parser.add_argument("--request-delay", type=float, default=0.5)
    parser.add_argument("--max-page-failures", type=int, default=5)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    configure_logging(args.log_level)

    output_dir = output_directory(args.output_dir, args.page_name)
    followers_path = output_dir / "followers_info.csv"
    checkpoint_path = output_dir / "followers_checkpoint.json"

    clients = build_clients(mode=0)
    account = retry_call(
        clients[0].get_account,
        args.page_name,
        attempts=args.request_attempts,
    )
    account_id = getattr(account, "identifier", None)
    if not account_id:
        raise RuntimeError("Instagram response did not contain an account identifier")

    checkpoint = load_json(checkpoint_path) if args.resume else {}
    cursor = checkpoint.get("cursor") if checkpoint else None
    followers = load_csv(followers_path) if args.resume else pd.DataFrame()
    consecutive_failures = 0
    has_next = True

    LOGGER.info("Starting follower collection for %s", args.page_name)

    while has_next:
        client = choose_client(clients)
        try:
            payload, has_next = retry_call(
                client.get_followers,
                account_id=account_id,
                count=args.page_size,
                end_cursor=cursor,
                attempts=args.request_attempts,
            )
        except Exception as exc:
            consecutive_failures += 1
            LOGGER.error("Follower page failed: %s", exc)
            if consecutive_failures >= args.max_page_failures:
                raise RuntimeError(
                    f"Stopped after {consecutive_failures} consecutive follower-page failures"
                ) from exc
            continue

        consecutive_failures = 0
        accounts = payload.get("accounts", []) if isinstance(payload, dict) else []
        next_cursor = payload.get("next_page") if isinstance(payload, dict) else None
        followers = pd.concat([followers, accounts_to_frame(accounts)], ignore_index=True)

        if "user_ID" in followers.columns:
            followers = followers.drop_duplicates(subset=["user_ID"], keep="last")

        cursor = next_cursor
        atomic_write_csv(followers, followers_path, index=False)
        save_json(
            {
                "page_name": args.page_name,
                "cursor": cursor,
                "has_next": bool(has_next),
                "records": len(followers),
            },
            checkpoint_path,
        )
        LOGGER.info("Saved %s follower records", len(followers))

        if args.request_delay > 0 and has_next:
            time.sleep(args.request_delay)

        if has_next and not cursor:
            LOGGER.warning("Instagram reported another page but returned no cursor; stopping")
            break

    save_json(
        {
            "page_name": args.page_name,
            "cursor": cursor,
            "has_next": False,
            "records": len(followers),
            "completed": True,
        },
        checkpoint_path,
    )
    LOGGER.info("Finished: %s follower records", len(followers))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
