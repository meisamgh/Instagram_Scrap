"""Shared runtime utilities for the scraper entry points."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, TypeVar
import json
import logging
import os
import random
import time

import pandas as pd
from dotenv import load_dotenv

from igramscraper.instagram import Instagram

T = TypeVar("T")
LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class AccountCredentials:
    username: str
    password: str


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def load_accounts() -> list[AccountCredentials]:
    """Load one or more Instagram accounts from environment variables.

    Preferred format:
        INSTAGRAM_ACCOUNTS_JSON='[{"username":"u1","password":"p1"}]'

    A single account can also use INSTAGRAM_USERNAME / INSTAGRAM_PASSWORD.
    """
    load_dotenv()
    raw = os.getenv("INSTAGRAM_ACCOUNTS_JSON")
    accounts: list[AccountCredentials] = []

    if raw:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("INSTAGRAM_ACCOUNTS_JSON must be valid JSON") from exc

        if not isinstance(payload, list):
            raise ValueError("INSTAGRAM_ACCOUNTS_JSON must contain a JSON list")

        for item in payload:
            if not isinstance(item, dict):
                raise ValueError("Each account entry must be a JSON object")
            username = str(item.get("username", "")).strip()
            password = str(item.get("password", ""))
            if username and password:
                accounts.append(AccountCredentials(username, password))
    else:
        username = os.getenv("INSTAGRAM_USERNAME", "").strip()
        password = os.getenv("INSTAGRAM_PASSWORD", "")
        if username and password:
            accounts.append(AccountCredentials(username, password))

    if not accounts:
        raise RuntimeError(
            "No Instagram credentials configured. Copy .env.example to .env and "
            "set INSTAGRAM_ACCOUNTS_JSON or INSTAGRAM_USERNAME/INSTAGRAM_PASSWORD."
        )

    return accounts


def build_clients(mode: int = 0) -> list[Instagram]:
    """Create authenticated clients, keeping any account that logs in successfully."""
    clients: list[Instagram] = []
    for account in load_accounts():
        try:
            client = Instagram(mode)
            client.with_credentials(account.username, account.password)
            client.login()
            clients.append(client)
            LOGGER.info("Authenticated Instagram session for %s", account.username)
        except Exception:
            LOGGER.exception("Could not authenticate account %s", account.username)

    if not clients:
        raise RuntimeError("None of the configured Instagram accounts could log in")
    return clients


def choose_client(clients: list[Instagram]) -> Instagram:
    if not clients:
        raise RuntimeError("No authenticated clients available")
    return random.choice(clients)


def retry_call(
    func: Callable[..., T],
    *args: Any,
    attempts: int = 4,
    base_delay: float = 1.0,
    max_delay: float = 20.0,
    **kwargs: Any,
) -> T:
    """Call a function with bounded exponential backoff and jitter."""
    if attempts < 1:
        raise ValueError("attempts must be >= 1")

    for attempt in range(1, attempts + 1):
        try:
            return func(*args, **kwargs)
        except Exception:
            if attempt == attempts:
                raise
            delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
            delay *= random.uniform(0.75, 1.25)
            LOGGER.warning(
                "Request failed (attempt %s/%s). Retrying in %.1fs",
                attempt,
                attempts,
                delay,
            )
            time.sleep(delay)

    raise RuntimeError("retry_call reached an unreachable state")


def output_directory(root: str | Path, page_name: str) -> Path:
    directory = Path(root).expanduser().resolve() / f"Data_{page_name}"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def atomic_write_csv(frame: pd.DataFrame, path: str | Path, *, index: bool = False) -> None:
    """Write a CSV via a temporary file so interrupted writes do not corrupt output."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    frame.to_csv(temporary, index=index)
    temporary.replace(destination)


def load_csv(path: str | Path) -> pd.DataFrame:
    source = Path(path)
    if not source.exists():
        return pd.DataFrame()
    return pd.read_csv(source)


def save_json(payload: dict[str, Any], path: str | Path) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    temporary.replace(destination)


def load_json(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    if not source.exists():
        return {}
    with source.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload if isinstance(payload, dict) else {}
