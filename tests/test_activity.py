"""Tests for the pure aggregation functions. No I/O, no mocking needed."""

import unittest
from datetime import datetime, timedelta, timezone

from gh_dashboard import activity


def _commit(repo, when):
    """Build a fake GitHub commit dict tagged with a repo, as recent_activity returns."""
    return {
        "repo": repo,
        "commit": {"author": {"date": when.strftime("%Y-%m-%dT%H:%M:%SZ")}},
    }


def _days_ago(n):
    return datetime.now(timezone.utc) - timedelta(days=n)


class CountByRepoTests(unittest.TestCase):
    def test_counts_commits_per_repo(self):
        commits = [
            _commit("a/one", _days_ago(0)),
            _commit("a/one", _days_ago(1)),
            _commit("b/two", _days_ago(0)),
        ]
        self.assertEqual(activity.count_by_repo(commits), {"a/one": 2, "b/two": 1})

    def test_empty_list_gives_empty_dict(self):
        self.assertEqual(activity.count_by_repo([]), {})


class ComputeStreakTests(unittest.TestCase):
    def test_no_commits_is_a_zero_streak(self):
        self.assertEqual(activity.compute_streak([]), (0, 0))

    def test_a_single_commit_today_is_a_streak_of_one(self):
        commits = [_commit("a/one", _days_ago(0))]
        self.assertEqual(activity.compute_streak(commits), (1, 1))

    def test_unbroken_run_ending_today(self):
        commits = [_commit("a/one", _days_ago(n)) for n in range(5)]
        self.assertEqual(activity.compute_streak(commits), (5, 5))

    def test_multiple_commits_on_one_day_count_once(self):
        today = _days_ago(0)
        commits = [
            _commit("a/one", today),
            _commit("a/one", today - timedelta(hours=3)),
            _commit("a/one", today - timedelta(hours=6)),
        ]
        self.assertEqual(activity.compute_streak(commits), (1, 1))

    def test_a_gap_makes_longest_differ_from_current(self):
        # Active 6-4 days ago (run of 3), silent for 2 days, active today only.
        commits = [_commit("a/one", _days_ago(n)) for n in (6, 5, 4, 0)]
        current, longest = activity.compute_streak(commits)
        self.assertEqual(current, 1)
        self.assertEqual(longest, 3)

    def test_no_commit_today_does_not_break_an_in_progress_streak(self):
        # Active yesterday and the day before, nothing today yet.
        commits = [_commit("a/one", _days_ago(n)) for n in (1, 2)]
        self.assertEqual(activity.compute_streak(commits), (2, 2))

    def test_a_gap_including_today_and_yesterday_resets_the_current_streak(self):
        # A real run 5-3 days ago, but silent yesterday and today.
        commits = [_commit("a/one", _days_ago(n)) for n in (5, 4, 3)]
        current, longest = activity.compute_streak(commits)
        self.assertEqual(current, 0)
        self.assertEqual(longest, 3)


if __name__ == "__main__":
    unittest.main()
