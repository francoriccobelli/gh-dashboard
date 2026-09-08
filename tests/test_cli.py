"""Tests for the CLI: parsing, dispatch, and each command's behaviour."""

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

    def test_summary_and_streak_accept_an_optional_days_flag(self):
        parser = cli.build_parser()

        summary_args = parser.parse_args(["summary"])
        self.assertIs(summary_args.func, cli.cmd_summary)
        self.assertEqual(summary_args.days, 30)

        streak_args = parser.parse_args(["streak"])
        self.assertIs(streak_args.func, cli.cmd_streak)
        self.assertEqual(streak_args.days, 90)

        self.assertEqual(parser.parse_args(["summary", "--days", "7"]).days, 7)

    def test_logout_takes_no_arguments(self):
        args = cli.build_parser().parse_args(["logout"])
        self.assertIs(args.func, cli.cmd_logout)

    def test_a_subcommand_is_required(self):
        with self.assertRaises(SystemExit):
            with contextlib.redirect_stderr(io.StringIO()):
                cli.build_parser().parse_args([])


class CliTestCase(ConfigFileTestCase):
    """Base for tests that run the CLI end to end against a temp config path."""

    def run_cli(self, argv):
        """Run main(argv), returning (exit_code, stdout, stderr)."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(argv)
        return code, out.getvalue(), err.getvalue()


class AuthTests(CliTestCase):
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


class LogoutTests(CliTestCase):
    def test_removes_an_existing_token(self):
        config.save_token("abc123")

        code, stdout, _ = self.run_cli(["logout"])

        self.assertEqual(code, 0)
        self.assertIn("Logged out", stdout)
        self.assertIsNone(config.load_token())

    def test_is_still_a_success_when_not_authenticated(self):
        code, stdout, _ = self.run_cli(["logout"])

        self.assertEqual(code, 0)
        self.assertIn("weren't logged in", stdout)

    def test_clears_a_corrupt_config_file_without_erroring(self):
        # This is the case the whole design is for: logout must be the
        # reliable way out of a corrupt config, not another command that
        # can fail on it.
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text("not json", encoding="utf-8")

        code, stdout, _ = self.run_cli(["logout"])

        self.assertEqual(code, 0)
        self.assertIn("Logged out", stdout)
        self.assertFalse(self.config_path.exists())


class SummaryTests(CliTestCase):
    def test_not_authenticated_is_a_clean_error(self):
        code, _, stderr = self.run_cli(["summary"])
        self.assertEqual(code, 1)
        self.assertIn("not authenticated", stderr)

    @mock.patch("gh_dashboard.cli.github_api.recent_activity")
    def test_not_authenticated_never_calls_recent_activity(self, mock_recent):
        self.run_cli(["summary"])
        mock_recent.assert_not_called()

    @mock.patch("gh_dashboard.cli.github_api.recent_activity")
    def test_prints_totals_and_a_per_repo_breakdown(self, mock_recent):
        config.save_token("abc123")
        mock_recent.return_value = [
            {"repo": "a/one"},
            {"repo": "a/one"},
            {"repo": "b/two"},
        ]

        code, stdout, _ = self.run_cli(["summary"])

        self.assertEqual(code, 0)
        self.assertIn("3 commits across 2 repositories", stdout)
        self.assertIn("a/one", stdout)
        self.assertIn("b/two", stdout)
        mock_recent.assert_called_once_with("abc123", 30)  # default --days

    @mock.patch("gh_dashboard.cli.github_api.recent_activity")
    def test_days_flag_is_passed_through(self, mock_recent):
        config.save_token("abc123")
        mock_recent.return_value = []

        self.run_cli(["summary", "--days", "7"])

        mock_recent.assert_called_once_with("abc123", 7)

    @mock.patch("gh_dashboard.cli.github_api.recent_activity")
    def test_a_github_error_is_rendered_and_exits_1(self, mock_recent):
        config.save_token("abc123")
        mock_recent.side_effect = github_api.GitHubError("boom")

        code, _, stderr = self.run_cli(["summary"])

        self.assertEqual(code, 1)
        self.assertIn("boom", stderr)

    def test_corrupt_config_file_is_a_clean_error(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text("not json", encoding="utf-8")

        code, _, stderr = self.run_cli(["summary"])

        self.assertEqual(code, 1)
        self.assertIn("error:", stderr)


class StreakTests(CliTestCase):
    def test_not_authenticated_is_a_clean_error(self):
        code, _, stderr = self.run_cli(["streak"])
        self.assertEqual(code, 1)
        self.assertIn("not authenticated", stderr)

    @mock.patch("gh_dashboard.cli.activity.compute_streak")
    @mock.patch("gh_dashboard.cli.github_api.recent_activity")
    def test_prints_current_and_longest(self, mock_recent, mock_streak):
        config.save_token("abc123")
        mock_recent.return_value = []
        mock_streak.return_value = (5, 12)

        code, stdout, _ = self.run_cli(["streak"])

        self.assertEqual(code, 0)
        self.assertIn("Current streak: 5 days", stdout)
        self.assertIn("Longest streak in the last 90 days: 12 days", stdout)
        mock_recent.assert_called_once_with("abc123", 90)  # default --days

    @mock.patch("gh_dashboard.cli.github_api.recent_activity")
    def test_days_flag_is_passed_through(self, mock_recent):
        config.save_token("abc123")
        mock_recent.return_value = []

        self.run_cli(["streak", "--days", "365"])

        mock_recent.assert_called_once_with("abc123", 365)

    @mock.patch("gh_dashboard.cli.github_api.recent_activity")
    def test_a_github_error_is_rendered_and_exits_1(self, mock_recent):
        config.save_token("abc123")
        mock_recent.side_effect = github_api.GitHubError("boom")

        code, _, stderr = self.run_cli(["streak"])

        self.assertEqual(code, 1)
        self.assertIn("boom", stderr)


if __name__ == "__main__":
    unittest.main()
