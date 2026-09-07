"""Placeholder tests for the CLI scaffold.

These check the wiring only — that the three planned subcommands parse and
dispatch. Real behaviour tests arrive with the implementations.
"""

import contextlib
import io
import unittest
from unittest import mock

from gh_dashboard import cli, config, github_api
from _helpers import ConfigFileTestCase


class ParserTests(unittest.TestCase):
    def test_auth_takes_a_token(self):
        args = cli.build_parser().parse_args(["auth", "abc123"])
        self.assertEqual(args.token, "abc123")
        self.assertIs(args.func, cli.cmd_auth)

    def test_summary_and_streak_take_no_arguments(self):
        parser = cli.build_parser()
        self.assertIs(parser.parse_args(["summary"]).func, cli.cmd_summary)
        self.assertIs(parser.parse_args(["streak"]).func, cli.cmd_streak)

    def test_a_subcommand_is_required(self):
        with self.assertRaises(SystemExit):
            with contextlib.redirect_stderr(io.StringIO()):
                cli.build_parser().parse_args([])


class DispatchTests(unittest.TestCase):
    def run_cli(self, argv):
        """Run main(argv), returning (exit_code, stdout)."""
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(argv)
        return code, out.getvalue()

    def test_still_stubbed_commands_succeed_and_say_so(self):
        for argv in (["summary"], ["streak"]):
            with self.subTest(argv=argv):
                code, stdout = self.run_cli(argv)
                self.assertEqual(code, 0)
                self.assertIn(cli.NOT_IMPLEMENTED, stdout)


class AuthTests(ConfigFileTestCase):
    def run_cli(self, argv):
        """Run main(argv), returning (exit_code, stdout, stderr)."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(argv)
        return code, out.getvalue(), err.getvalue()

    @mock.patch("gh_dashboard.cli.github_api.verify_token")
    def test_success_stores_the_token_and_greets_the_user(self, mock_verify):
        mock_verify.return_value = {"login": "octocat"}

        code, stdout, _ = self.run_cli(["auth", "abc123"])

        self.assertEqual(code, 0)
        self.assertIn("octocat", stdout)
        mock_verify.assert_called_once_with("abc123")
        # Real save_token/load_token ran against the patched temp path.
        self.assertEqual(config.load_token(), "abc123")

    @mock.patch("gh_dashboard.cli.github_api.verify_token")
    def test_rejected_token_is_not_stored(self, mock_verify):
        mock_verify.side_effect = github_api.GitHubError("nope")

        code, _, stderr = self.run_cli(["auth", "abc123"])

        self.assertEqual(code, 1)
        self.assertIn("nope", stderr)
        self.assertIsNone(config.load_token())

    @mock.patch("gh_dashboard.cli.github_api.verify_token")
    def test_blank_token_is_rejected_without_a_network_call(self, mock_verify):
        code, _, stderr = self.run_cli(["auth", "   "])

        self.assertEqual(code, 1)
        self.assertIn("empty", stderr)
        mock_verify.assert_not_called()


if __name__ == "__main__":
    unittest.main()
