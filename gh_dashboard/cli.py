"""Command-line entry point: argparse, dispatch, and printing.

This module opens no files and makes no network calls of its own. It asks
:mod:`gh_dashboard.config` for the stored token and hands it to
:mod:`gh_dashboard.github_api`, then prints what comes back.

Handlers return an exit code rather than calling ``sys.exit``, so tests can
call them directly and assert on the return value.
"""

from __future__ import annotations

import argparse
import sys

from . import __version__, activity, config, github_api


def _token_or_hint() -> str | None:
    """Return the stored token, or print a hint and return ``None`` if there isn't one."""
    token = config.load_token()
    if token is None:
        print(
            "error: not authenticated - run `gh-dashboard auth <token>` first",
            file=sys.stderr,
        )
    return token


def cmd_auth(args: argparse.Namespace) -> int:
    """Verify a GitHub personal access token and store it for later commands.

    Rejects a blank token before making a network call. Everything else —
    a rejected token, a filesystem error while saving — propagates as an
    exception for :func:`main` to render; this handler has no try/except of
    its own.
    """
    token = args.token.strip()
    if not token:
        print("error: token must not be empty", file=sys.stderr)
        return 1

    user = github_api.verify_token(token)
    config.save_token(token)
    print(f"Authenticated as {user['login']}")
    return 0


def cmd_logout(args: argparse.Namespace) -> int:
    """Remove any stored GitHub access token.

    Deliberately never calls :func:`config.load_token`, which parses the file
    and can raise ``ValueError`` on a corrupt one — this command needs to be
    the reliable way *out* of that state, not another way to hit it. Checking
    existence directly and clearing unconditionally both succeed regardless
    of whether the file is valid JSON.
    """
    was_authenticated = config.config_file().exists()
    config.clear_token()
    print("Logged out." if was_authenticated else "You weren't logged in.")
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    """Print a commit count and per-repo breakdown for the last ``args.days`` days."""
    token = _token_or_hint()
    if token is None:
        return 1

    commits = github_api.recent_activity(token, args.days)
    counts = activity.count_by_repo(commits)
    total = sum(counts.values())

    commit_word = "commit" if total == 1 else "commits"
    repo_word = "repository" if len(counts) == 1 else "repositories"
    print(f"Last {args.days} days: {total} {commit_word} across {len(counts)} {repo_word}")

    top_repos = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:5]
    for repo, count in top_repos:
        print(f"  {repo:<30} {count}")
    return 0


def cmd_streak(args: argparse.Namespace) -> int:
    """Print the current and longest run of consecutive days with a commit."""
    token = _token_or_hint()
    if token is None:
        return 1

    commits = github_api.recent_activity(token, args.days)
    current, longest = activity.compute_streak(commits)

    print(f"Current streak: {current} day{'s' if current != 1 else ''}")
    print(
        f"Longest streak in the last {args.days} days: "
        f"{longest} day{'s' if longest != 1 else ''}"
    )
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

    logout = subparsers.add_parser("logout", help="remove the stored GitHub access token")
    logout.set_defaults(func=cmd_logout)

    summary = subparsers.add_parser("summary", help="summarize recent activity")
    summary.add_argument(
        "--days", type=int, default=30, help="how many days back to look (default: 30)"
    )
    summary.set_defaults(func=cmd_summary)

    streak = subparsers.add_parser("streak", help="show your current commit streak")
    streak.add_argument(
        "--days", type=int, default=90, help="how many days back to look (default: 90)"
    )
    streak.set_defaults(func=cmd_streak)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse ``argv`` and run the requested command, returning its exit code.

    ``argv`` defaults to ``sys.argv[1:]``; taking it as a parameter is what
    lets tests drive ``main`` directly. This is also the single place that
    turns a ``GitHubError``, an ``OSError``, or a ``ValueError`` (a corrupt
    config file) into a one-line stderr message, so no handler needs its own
    try/except.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (github_api.GitHubError, OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
