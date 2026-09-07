"""GitHub REST API wrapper: HTTP in, plain data out.

Every function here takes a token plus arguments and returns plain Python data
(dicts and lists straight off the JSON). It never prints, and it never touches
the config file — the caller reads the token from :mod:`gh_dashboard.config`
and passes it in, which is what keeps this module testable against a fake
response instead of a live account.

Failures surface as :class:`GitHubError` so ``cli.main`` has one exception type
to turn into a one-line message.
"""

from __future__ import annotations

from typing import Any

import requests

API_ROOT = "https://api.github.com"

#: Sent on every request; GitHub asks callers to pin the API version.
API_VERSION = "2022-11-28"

#: GitHub rejects requests with no User-Agent.
USER_AGENT = "gh-dashboard"

#: Fail rather than hang if GitHub (or the network) doesn't respond.
TIMEOUT_SECONDS = 10


class GitHubError(Exception):
    """A request to GitHub failed: network trouble, bad token, or rate limit."""


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": API_VERSION,
        "User-Agent": USER_AGENT,
    }


def verify_token(token: str) -> dict[str, Any]:
    """Confirm ``token`` works and return the authenticated user.

    ``GET /user``. Used by the ``auth`` command to fail fast on a bad token
    rather than storing one that will not work. Raises :class:`GitHubError` if
    GitHub rejects the credentials, returns an error, or can't be reached.
    """
    try:
        response = requests.get(
            f"{API_ROOT}/user",
            headers=_headers(token),
            timeout=TIMEOUT_SECONDS,
        )
    except requests.RequestException as e:
        raise GitHubError(f"could not reach GitHub: {e}") from e

    if response.status_code == 401:
        raise GitHubError("GitHub rejected the token (401 Unauthorized)")
    if not response.ok:
        raise GitHubError(f"GitHub returned {response.status_code}")
    return response.json()


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
