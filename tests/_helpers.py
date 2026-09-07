"""Shared test helpers.

Leading underscore keeps this out of unittest/pytest discovery — it is not
itself a test module.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from gh_dashboard import config


class ConfigFileTestCase(unittest.TestCase):
    """Redirects ``config.CONFIG_FILE`` to a temp path for the duration of a test.

    Every test that touches ``config.save_token`` / ``load_token`` /
    ``clear_token`` must inherit from this — never let a test reach the real
    ``~/.gh_dashboard/config.json``.
    """

    def setUp(self) -> None:
        super().setUp()
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        # One level under tmpdir, which TemporaryDirectory already created —
        # so config_path.parent does *not* exist yet, same as production
        # (CONFIG_DIR is a subdirectory of home, not home itself). That's
        # what lets a test assert save_token() creates it.
        self.config_path = Path(tmpdir.name) / "gh_dashboard" / "config.json"
        patcher = mock.patch.object(config, "CONFIG_FILE", self.config_path)
        patcher.start()
        self.addCleanup(patcher.stop)
