"""GitHub REST API wrapper: HTTP in, plain data out.

Every function here takes a token plus arguments and returns plain Python data
(dicts and lists straight off the JSON). It never prints, and it never touches
the config file — the caller reads the token from :mod:`gh_dashboard.config`
and passes it in, which is what keeps this module testable against a fake
response instead of a live account.

Failures surface as :class:`GitHubError` so ``cli.main`` has one exception type
to turn into a one-line message.

Nothing here is implemented yet — the functions below record the intended
shape. ``requests`` stays unimported until something actually issues a request.
"""

from __future__ import annotations

from typing import Any

API_ROOT = "https://api.github.com"

#: Sent on every request; GitHub asks callers to pin the API version.
API_VERSION = "2022-11-28"


class GitHubError(Exception):
    """A request to GitHub failed: network trouble, bad token, or rate limit."""


def verify_token(token: str) -> dict[str, Any]:
    """Confirm ``token`` works and return the authenticated user.

    ``GET /user``. Used by the ``auth`` command to fail fast on a bad token
    rather than storing one that will not work. Raises :class:`GitHubError` if
    GitHub rejects the credentials.
    """
    raise NotImplementedError


def list_repos(token: str) -> list[dict[str, Any]]:
    """Return the repositories the authenticated user can see.

    ``GET /user/repos``. Follows pagination to the end and returns the pages
    already flattened into one list.
    """
    raise NotImplementedError


def list_commits(token: str, repo: str, since: str) -> list[dict[str, Any]]:
    """Return the user's commits in ``repo`` on or after ``since``.

    ``GET /repos/{repo}/commits``. ``repo`` is ``owner/name``; ``since`` is an
    ISO-8601 timestamp, which is the format GitHub expects on the wire.
    """
    raise NotImplementedError


def recent_activity(token: str, days: int) -> list[dict[str, Any]]:
    """Return the user's commit activity over the last ``days`` days.

    The one call ``summary`` and ``streak`` are both built on: fans out over
    the user's repositories, collects commits in the window, and returns them
    as a flat list for the caller to aggregate.
    """
    raise NotImplementedError
