"""Collect liker metadata for posts from a public Instagram account.

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

LOGGER = logging.getLogger("likes")


def normalize_likes(short_code: str, likes: Any) -> pd.DataFrame:
    if isinstance(likes, pd.DataFrame):
        frame = likes.copy()
    elif isinstance(likes, list):
        frame = pd.DataFrame([dict(vars(item)) if hasattr(item, "__dict__") else item for item in likes])
    else:
        return pd.DataFrame()

    if frame.empty:
        return frame

    if "identifier" in frame.columns and "user_ID" not in frame.columns:
        frame = frame.rename(columns={"identifier": "user_ID"})
    if "id" in frame.columns and "user_ID" not in frame.columns:
        frame = frame.rename(columns={"id": "user_ID"})
    frame["short_code"] = short_code
    frame["scraping_time"] = pd.Timestamp.utcnow()
    return frame


def save_outputs(likes: pd.DataFrame, output_dir, state: dict[str, Any]) -> None:
    if not likes.empty:
        dedupe_columns = [column for column in ("short_code", "user_ID") if column in likes.columns]
        if dedupe_columns:
            likes = likes.drop_duplicates(subset=dedupe_columns, keep="last")
    atomic_write_csv(likes, output_dir / "likes.csv", index=False)
    save_json(state, output_dir / "likes_checkpoint.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect Instagram post likes")
    parser.add_argument("page_name", help="Target public Instagram username")
    parser.add_argument("--output-dir", default=os.getenv("OUTPUT_PATH", "./data"))
    parser.add_argument("--num-posts", type=int, default=None)
    parser.add_argument("--page-size", type=int, default=50)
    parser.add_argument("--checkpoint-seconds", type=int, default=300)
    parser.add_argument("--request-attempts", type=int, default=4)
    parser.add_argument("--max-item-failures", type=int, default=3)
    parser.add_argument("--request-delay", type=float, default=0.5)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    configure_logging(args.log_level)

    output_dir = output_directory(args.output_dir, args.page_name)
    checkpoint_path = output_dir / "likes_checkpoint.json"
    page_info_path = output_dir / "page_info.csv"

    clients = build_clients(mode=1)
    account = retry_call(
        clients[0].get_account,
        args.page_name,
        attempts=args.request_attempts,
    )

    checkpoint = load_json(checkpoint_path) if args.resume else {}
    if args.resume and page_info_path.exists():
        media_frame = load_csv(page_info_path)
    else:
        media_count = int(getattr(account, "media_count", 0) or 0)
        num_posts = args.num_posts if args.num_posts is not None else media_count
        media = retry_call(
            clients[0].get_medias,
            args.page_name,
            num_posts,
            attempts=args.request_attempts,
        )
        media_frame = pd.DataFrame([dict(vars(item)) for item in media])
        atomic_write_csv(media_frame, page_info_path, index=False)

    if "short_code" not in media_frame.columns:
        raise RuntimeError("Could not find post short codes in Instagram response")

    if "likes_count" in media_frame.columns:
        media_frame = media_frame.sort_values("likes_count")
    short_codes = [str(value) for value in media_frame["short_code"].dropna().tolist()]

    cursors = checkpoint.get("cursors", {}) if checkpoint else {}
    pending = checkpoint.get("pending", short_codes.copy()) if checkpoint else short_codes.copy()
    failures = checkpoint.get("failures", {}) if checkpoint else {}
    failed = checkpoint.get("failed", []) if checkpoint else []
    likes = load_csv(output_dir / "likes.csv") if args.resume else pd.DataFrame()
    last_checkpoint = time.monotonic()

    LOGGER.info("Starting like collection for %s (%s posts pending)", args.page_name, len(pending))

    while pending:
        progress_this_pass = False
        for short_code in list(pending):
            previous_cursor = cursors.get(short_code)
            client = choose_client(clients)
            try:
                batch, max_id, has_next = retry_call(
                    client.get_media_likes_by_code,
                    short_code,
                    args.page_size,
                    max_id=previous_cursor,
                    attempts=args.request_attempts,
                )
            except Exception as exc:
                failures[short_code] = int(failures.get(short_code, 0)) + 1
                LOGGER.error("Post %s failed: %s", short_code, exc)
                if failures[short_code] >= args.max_item_failures:
                    pending.remove(short_code)
                    failed.append(short_code)
                    LOGGER.error("Giving up on post %s after %s failures", short_code, failures[short_code])
                continue

            progress_this_pass = True
            failures[short_code] = 0
            likes = pd.concat([likes, normalize_likes(short_code, batch)], ignore_index=True)

            if has_next and max_id and max_id != previous_cursor:
                cursors[short_code] = max_id
            else:
                pending.remove(short_code)

            if args.request_delay > 0:
                time.sleep(args.request_delay)

            if time.monotonic() - last_checkpoint >= args.checkpoint_seconds:
                state = {
                    "page_name": args.page_name,
                    "cursors": cursors,
                    "pending": pending,
                    "failures": failures,
                    "failed": sorted(set(failed)),
                }
                save_outputs(likes, output_dir, state)
                LOGGER.info("Checkpoint saved (%s posts pending)", len(pending))
                last_checkpoint = time.monotonic()

        if not progress_this_pass and pending:
            LOGGER.warning("No progress in this pass; sleeping before retrying pending posts")
            time.sleep(max(1.0, args.request_delay))

    state = {
        "page_name": args.page_name,
        "cursors": cursors,
        "pending": [],
        "failures": failures,
        "failed": sorted(set(failed)),
        "completed": True,
    }
    save_outputs(likes, output_dir, state)
    LOGGER.info("Finished: %s like records, %s failed posts", len(likes), len(set(failed)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
