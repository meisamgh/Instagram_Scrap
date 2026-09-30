from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from scraper_runtime import atomic_write_csv, load_accounts, load_csv, load_json, save_json


class RuntimeTests(unittest.TestCase):
    def test_load_single_account_from_environment(self) -> None:
        env = {
            "INSTAGRAM_USERNAME": "example_user",
            "INSTAGRAM_PASSWORD": "example_password",
        }
        with patch.dict(os.environ, env, clear=True):
            accounts = load_accounts()
        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0].username, "example_user")
        self.assertEqual(accounts[0].password, "example_password")

    def test_load_multiple_accounts_from_json(self) -> None:
        env = {
            "INSTAGRAM_ACCOUNTS_JSON": (
                '[{"username":"one","password":"p1"},'
                '{"username":"two","password":"p2"}]'
            )
        }
        with patch.dict(os.environ, env, clear=True):
            accounts = load_accounts()
        self.assertEqual([account.username for account in accounts], ["one", "two"])

    def test_atomic_csv_and_json_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csv_path = root / "records.csv"
            json_path = root / "state.json"

            expected = pd.DataFrame([{"id": 1, "name": "example"}])
            atomic_write_csv(expected, csv_path, index=False)
            save_json({"cursor": "abc", "pending": ["x"]}, json_path)

            actual = load_csv(csv_path)
            state = load_json(json_path)

            self.assertEqual(actual.to_dict("records"), expected.to_dict("records"))
            self.assertEqual(state["cursor"], "abc")
            self.assertEqual(state["pending"], ["x"])


if __name__ == "__main__":
    unittest.main()
