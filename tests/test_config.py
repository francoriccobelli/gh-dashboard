"""Tests for local token storage.

Every test here runs against a temp path via ConfigFileTestCase — never the
real ~/.gh_dashboard/config.json.
"""

import json
import sys
import unittest

from gh_dashboard import config
from _helpers import ConfigFileTestCase


class LoadTokenTests(ConfigFileTestCase):
    def test_returns_none_when_no_file_exists(self):
        self.assertIsNone(config.load_token())

    def test_raises_value_error_on_invalid_json(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text("not json", encoding="utf-8")
        with self.assertRaises(ValueError):
            config.load_token()

    def test_raises_value_error_when_token_key_missing(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(json.dumps({"other": "stuff"}), encoding="utf-8")
        with self.assertRaises(ValueError):
            config.load_token()

    def test_raises_value_error_when_token_is_not_a_string(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(json.dumps({"token": 123}), encoding="utf-8")
        with self.assertRaises(ValueError):
            config.load_token()


class SaveTokenTests(ConfigFileTestCase):
    def test_round_trips_through_save_and_load(self):
        config.save_token("abc123")
        self.assertEqual(config.load_token(), "abc123")

    def test_creates_the_parent_directory(self):
        self.assertFalse(self.config_path.parent.exists())
        config.save_token("abc123")
        self.assertTrue(self.config_path.exists())

    def test_rejects_a_blank_token(self):
        with self.assertRaises(ValueError):
            config.save_token("   ")
        self.assertIsNone(config.load_token())

    def test_strips_surrounding_whitespace(self):
        config.save_token("  abc123  ")
        self.assertEqual(config.load_token(), "abc123")

    @unittest.skipIf(
        sys.platform == "win32",
        "POSIX permission bits aren't meaningful on Windows",
    )
    def test_file_is_owner_only(self):
        config.save_token("abc123")
        mode = self.config_path.stat().st_mode & 0o777
        self.assertEqual(mode, 0o600)


class ClearTokenTests(ConfigFileTestCase):
    def test_removes_an_existing_token(self):
        config.save_token("abc123")
        config.clear_token()
        self.assertIsNone(config.load_token())

    def test_is_a_silent_no_op_when_nothing_is_stored(self):
        config.clear_token()  # must not raise
        self.assertIsNone(config.load_token())


if __name__ == "__main__":
    unittest.main()
