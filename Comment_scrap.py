"""Collect comments and replies for a public Instagram account.

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

LOGGER = logging.getLogger("comments")


def objects_to_frame(short_code: str, objects: list[Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for item in objects:
        row = dict(vars(item))
        owner = row.pop("owner", None)
        row["id_comments"] = row.pop("identifier", None)
        row["short_code"] = short_code
        if owner is not None:
            owner_data = dict(vars(owner))
            row["user_ID"] = owner_data.pop("identifier", None)
            for key, value in owner_data.items():
                row.setdefault(f"owner_{key}", value)
        rows.append(row)
    return pd.DataFrame(rows)


def replies_to_frame(short_code: str, replies: Any) -> pd.DataFrame:
    if replies is None:
        return pd.DataFrame()
    if isinstance(replies, pd.DataFrame):
        frame = replies.copy()
    elif isinstance(replies, list):
        frame = pd.DataFrame([dict(vars(item)) if hasattr(item, "__dict__") else item for item in replies])
    else:
        return pd.DataFrame()
    if not frame.empty and "short_code" not in frame.columns:
        frame["short_code"] = short_code
    return frame


def save_outputs(
    comments: pd.DataFrame,
    replies: pd.DataFrame,
    output_dir,
    state: dict[str, Any],
) -> None:
    if not comments.empty and "id_comments" in comments.columns:
        comments = comments.drop_duplicates(subset=["id_comments"], keep="last")
    if not replies.empty:
        dedupe_key = "identifier" if "identifier" in replies.columns else None
        replies = replies.drop_duplicates(subset=[dedupe_key] if dedupe_key else None, keep="last")

    atomic_write_csv(comments, output_dir / "comments.csv", index=False)
    atomic_write_csv(replies, output_dir / "replies.csv", index=False)
    save_json(state, output_dir / "comments_checkpoint.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect Instagram comments and replies")
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
    checkpoint_path = output_dir / "comments_checkpoint.json"
    page_info_path = output_dir / "page_info.csv"

    clients = build_clients(mode=0)
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

    short_codes = [str(value) for value in media_frame["short_code"].dropna().tolist()]
    cursors = checkpoint.get("cursors", {}) if checkpoint else {}
    pending = checkpoint.get("pending", short_codes.copy()) if checkpoint else short_codes.copy()
    failures = checkpoint.get("failures", {}) if checkpoint else {}
    failed = checkpoint.get("failed", []) if checkpoint else []

    comments = load_csv(output_dir / "comments.csv") if args.resume else pd.DataFrame()
    replies = load_csv(output_dir / "replies.csv") if args.resume else pd.DataFrame()
    last_checkpoint = time.monotonic()

    LOGGER.info("Starting comment collection for %s (%s posts pending)", args.page_name, len(pending))

    while pending:
        progress_this_pass = False
        for short_code in list(pending):
            previous_cursor = cursors.get(short_code)
            client = choose_client(clients)
            try:
                batch, max_id, has_next, batch_replies = retry_call(
                    client.get_media_comments_by_code,
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
            comments = pd.concat([comments, objects_to_frame(short_code, batch)], ignore_index=True)
            replies = pd.concat([replies, replies_to_frame(short_code, batch_replies)], ignore_index=True)

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
                save_outputs(comments, replies, output_dir, state)
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
    save_outputs(comments, replies, output_dir, state)
    LOGGER.info("Finished: %s comments, %s replies, %s failed posts", len(comments), len(replies), len(set(failed)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
