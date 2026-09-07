"""GitHub REST API wrapper: HTTP in, plain data out.

Every function here takes a token plus arguments and returns plain Python data
(dicts and lists straight off the JSON, or — for :func:`recent_activity`,
which combines several calls — that same shape with one field added). It
never prints, and it never touches the config file — the caller reads the
token from :mod:`gh_dashboard.config` and passes it in, which is what keeps
this module testable against a fake response instead of a live account.

Failures surface as :class:`GitHubError` so ``cli.main`` has one exception type
to turn into a one-line message.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
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


def _parse_github_datetime(value: str) -> datetime:
    """Parse a GitHub timestamp (``...Z``) into an aware UTC datetime.

    ``datetime.fromisoformat`` only grew ``Z``-suffix support in Python 3.11;
    this project supports 3.10, hence the manual swap.
    """
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _paginated_get(
    url: str,
    token: str,
    params: dict[str, Any] | None = None,
    *,
    empty_status: int | None = None,
) -> list[dict[str, Any]]:
    """GET ``url``, following ``rel="next"`` Link headers until exhausted.

    Flattens every page's JSON array into one list. If ``empty_status`` is
    given and GitHub responds with that status, treats it as an empty result
    rather than an error — used for the ``409`` GitHub returns for a
    repository with no commits yet, which is a real, benign case.
    """
    results: list[dict[str, Any]] = []
    while url:
        try:
            response = requests.get(
                url, headers=_headers(token), params=params, timeout=TIMEOUT_SECONDS
            )
        except requests.RequestException as e:
            raise GitHubError(f"could not reach GitHub: {e}") from e

        if empty_status is not None and response.status_code == empty_status:
            return results
        if response.status_code == 401:
            raise GitHubError("GitHub rejected the token (401 Unauthorized)")
        if not response.ok:
            raise GitHubError(f"GitHub returned {response.status_code}")

        results.extend(response.json())
        url = response.links.get("next", {}).get("url")
        params = None  # the next page's URL already carries its own query string

    return results


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

    ``GET /user/repos``, sorted by most-recently-pushed. Follows pagination to
    the end and returns the pages already flattened into one list — a
    complete listing, not filtered to any window (that's :func:`recent_activity`'s
    job, since a future command might want the full list for its own reasons).
    """
    return _paginated_get(
        f"{API_ROOT}/user/repos",
        token,
        params={"per_page": 100, "sort": "pushed", "direction": "desc"},
    )


def list_commits(
    token: str, repo: str, since: str, author: str | None = None
) -> list[dict[str, Any]]:
    """Return commits in ``repo`` on or after ``since``, optionally by one author.

    ``GET /repos/{repo}/commits``. ``repo`` is ``owner/name``; ``since`` is an
    ISO-8601 timestamp, the format GitHub expects on the wire. ``author``, if
    given, is a GitHub username or email and filters to that person's commits
    only — GitHub's own query parameter, passed straight through. A
    repository with no commits yet returns ``[]`` rather than raising.
    """
    params: dict[str, Any] = {"per_page": 100, "since": since}
    if author is not None:
        params["author"] = author
    return _paginated_get(
        f"{API_ROOT}/repos/{repo}/commits", token, params=params, empty_status=409
    )


def recent_activity(token: str, days: int) -> list[dict[str, Any]]:
    """Return the user's commit activity over the last ``days`` days.

    The one call ``summary`` and ``streak`` are both built on: finds the
    authenticated user's login, fans out over their repositories — skipping
    any whose ``pushed_at`` predates the window, since nobody (this user
    included) pushed to it during the window either — and collects that
    user's commits from each remaining repo into one flat list. Each commit
    is the raw GitHub commit object plus a ``"repo"`` key (``owner/name``),
    since the raw payload doesn't otherwise say which repo it came from.
    """
    login = verify_token(token)["login"]
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    since = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

    activity: list[dict[str, Any]] = []
    for repo in list_repos(token):
        pushed_at = repo.get("pushed_at")
        if pushed_at is None or _parse_github_datetime(pushed_at) < cutoff:
            continue
        full_name = repo["full_name"]
        for commit in list_commits(token, full_name, since, author=login):
            activity.append({**commit, "repo": full_name})
    return activity
