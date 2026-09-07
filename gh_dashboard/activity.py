"""Pure aggregation over the commit data github_api.recent_activity returns.

No I/O, no printing, no GitHub calls — every function here takes the flat
commit list :func:`gh_dashboard.github_api.recent_activity` produces and
returns plain data. That split is what keeps this testable without a network
connection or an argparse namespace, the same reasoning behind the
config/github_api split.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any


def _commit_date(commit: dict[str, Any]) -> date:
    """Extract the calendar day (UTC) a commit was authored on."""
    raw = commit["commit"]["author"]["date"]
    return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()


def count_by_repo(commits: list[dict[str, Any]]) -> dict[str, int]:
    """Return ``{repo: commit count}``, in the order each repo was first seen."""
    counts: dict[str, int] = {}
    for commit in commits:
        repo = commit["repo"]
        counts[repo] = counts.get(repo, 0) + 1
    return counts


def compute_streak(commits: list[dict[str, Any]]) -> tuple[int, int]:
    """Return ``(current_streak, longest_streak)`` in days.

    A day "counts" if it has at least one commit; duplicates and multiple
    commits on the same day all collapse to that one active day. The current
    streak counts backward from the most recent active day — today, or
    yesterday if today has no commit *yet* (today not being over yet doesn't
    break an in-progress streak); if neither today nor yesterday is active,
    the current streak is 0, even if ``longest`` found a run earlier in the
    data. Both numbers are bounded by whatever window the caller fetched
    commits for — a streak older than that window is invisible here.
    """
    active_days = {_commit_date(c) for c in commits}
    if not active_days:
        return 0, 0

    ordered = sorted(active_days)
    longest = run = 1
    for prev_day, day in zip(ordered, ordered[1:]):
        run = run + 1 if day == prev_day + timedelta(days=1) else 1
        longest = max(longest, run)

    today = datetime.now(timezone.utc).date()
    if today in active_days:
        anchor = today
    elif today - timedelta(days=1) in active_days:
        anchor = today - timedelta(days=1)
    else:
        return 0, longest

    current = 1
    day = anchor
    while (day - timedelta(days=1)) in active_days:
        day -= timedelta(days=1)
        current += 1

    return current, longest
