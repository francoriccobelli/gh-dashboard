"""Placeholder tests for the CLI scaffold.

These check the wiring only — that the three planned subcommands parse and
dispatch. Real behaviour tests arrive with the implementations.
"""

import contextlib
import io
import unittest

from gh_dashboard import cli


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

    def test_every_command_succeeds_and_says_it_is_a_stub(self):
        for argv in (["auth", "abc123"], ["summary"], ["streak"]):
            with self.subTest(argv=argv):
                code, stdout = self.run_cli(argv)
                self.assertEqual(code, 0)
                self.assertIn(cli.NOT_IMPLEMENTED, stdout)


if __name__ == "__main__":
    unittest.main()
