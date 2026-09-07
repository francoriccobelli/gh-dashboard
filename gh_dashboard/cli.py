"""Command-line entry point: argparse, dispatch, and printing.

This module opens no files and makes no network calls of its own. It asks
:mod:`gh_dashboard.config` for the stored token and hands it to
:mod:`gh_dashboard.github_api`, then prints what comes back.

Handlers return an exit code rather than calling ``sys.exit``, so tests can
call them directly and assert on the return value.
"""

from __future__ import annotations

import argparse

from . import __version__

NOT_IMPLEMENTED = "not implemented yet"


def cmd_auth(args: argparse.Namespace) -> int:
    """Store a GitHub personal access token for later commands."""
    print(NOT_IMPLEMENTED)
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    """Print a summary of recent GitHub activity."""
    print(NOT_IMPLEMENTED)
    return 0


def cmd_streak(args: argparse.Namespace) -> int:
    """Print the current run of consecutive days with commits."""
    print(NOT_IMPLEMENTED)
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser.

    Split out from :func:`main` so tests can inspect the parser and check
    ``--help`` without running a command.
    """
    parser = argparse.ArgumentParser(
        prog="gh-dashboard",
        description="Summarize your GitHub activity from the command line.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    auth = subparsers.add_parser("auth", help="store a GitHub access token")
    auth.add_argument("token", help="a GitHub personal access token")
    auth.set_defaults(func=cmd_auth)

    summary = subparsers.add_parser("summary", help="summarize recent activity")
    summary.set_defaults(func=cmd_summary)

    streak = subparsers.add_parser("streak", help="show your current commit streak")
    streak.set_defaults(func=cmd_streak)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse ``argv`` and run the requested command, returning its exit code.

    ``argv`` defaults to ``sys.argv[1:]``; taking it as a parameter is what
    lets tests drive ``main`` directly. This is also the single place that will
    turn a ``GitHubError`` or an ``OSError`` into a one-line stderr message, so
    no handler needs its own try/except.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
