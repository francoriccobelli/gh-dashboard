"""Tests for the GitHub REST API wrapper. No real HTTP: requests.get is mocked."""

import unittest
from unittest import mock

import requests

from gh_dashboard import github_api


def _fake_response(status_code, json_data=None, links=None):
    response = mock.Mock()
    response.status_code = status_code
    response.ok = 200 <= status_code < 300
    response.json.return_value = json_data
    response.links = links or {}
    return response


class VerifyTokenTests(unittest.TestCase):
    @mock.patch("gh_dashboard.github_api.requests.get")
    def test_returns_the_parsed_user_on_success(self, mock_get):
        mock_get.return_value = _fake_response(200, {"login": "octocat"})
        self.assertEqual(github_api.verify_token("tok"), {"login": "octocat"})

    @mock.patch("gh_dashboard.github_api.requests.get")
    def test_sends_a_bearer_authorization_header(self, mock_get):
        mock_get.return_value = _fake_response(200, {"login": "octocat"})
        github_api.verify_token("my-token")
        _, kwargs = mock_get.call_args
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer my-token")

    @mock.patch("gh_dashboard.github_api.requests.get")
    def test_raises_github_error_on_401(self, mock_get):
        mock_get.return_value = _fake_response(401)
        with self.assertRaises(github_api.GitHubError):
            github_api.verify_token("bad-token")

    @mock.patch("gh_dashboard.github_api.requests.get")
    def test_raises_github_error_on_other_bad_status(self, mock_get):
        mock_get.return_value = _fake_response(500)
        with self.assertRaises(github_api.GitHubError):
            github_api.verify_token("tok")

    @mock.patch("gh_dashboard.github_api.requests.get")
    def test_raises_github_error_on_connection_failure(self, mock_get):
        mock_get.side_effect = requests.ConnectionError("boom")
        with self.assertRaises(github_api.GitHubError):
            github_api.verify_token("tok")


class ListReposTests(unittest.TestCase):
    @mock.patch("gh_dashboard.github_api.requests.get")
    def test_follows_pagination_and_flattens_the_pages(self, mock_get):
        page1 = _fake_response(
            200,
            [{"full_name": "octocat/repo1"}],
            links={"next": {"url": "https://api.github.com/user/repos?page=2"}},
        )
        page2 = _fake_response(200, [{"full_name": "octocat/repo2"}])
        mock_get.side_effect = [page1, page2]

        repos = github_api.list_repos("tok")

        self.assertEqual(
            [r["full_name"] for r in repos], ["octocat/repo1", "octocat/repo2"]
        )
        self.assertEqual(mock_get.call_count, 2)

    @mock.patch("gh_dashboard.github_api.requests.get")
    def test_sends_per_page_and_sort_params(self, mock_get):
        mock_get.return_value = _fake_response(200, [])
        github_api.list_repos("tok")
        _, kwargs = mock_get.call_args
        self.assertEqual(
            kwargs["params"],
            {"per_page": 100, "sort": "pushed", "direction": "desc"},
        )


class ListCommitsTests(unittest.TestCase):
    @mock.patch("gh_dashboard.github_api.requests.get")
    def test_sends_since_and_author(self, mock_get):
        mock_get.return_value = _fake_response(200, [])
        github_api.list_commits("tok", "octocat/repo", "2026-01-01T00:00:00Z", author="octocat")
        _, kwargs = mock_get.call_args
        self.assertEqual(kwargs["params"]["since"], "2026-01-01T00:00:00Z")
        self.assertEqual(kwargs["params"]["author"], "octocat")

    @mock.patch("gh_dashboard.github_api.requests.get")
    def test_author_is_omitted_when_not_given(self, mock_get):
        mock_get.return_value = _fake_response(200, [])
        github_api.list_commits("tok", "octocat/repo", "2026-01-01T00:00:00Z")
        _, kwargs = mock_get.call_args
        self.assertNotIn("author", kwargs["params"])

    @mock.patch("gh_dashboard.github_api.requests.get")
    def test_empty_repository_returns_empty_list(self, mock_get):
        mock_get.return_value = _fake_response(409)
        self.assertEqual(
            github_api.list_commits("tok", "octocat/empty-repo", "2026-01-01T00:00:00Z"), []
        )

    @mock.patch("gh_dashboard.github_api.requests.get")
    def test_follows_pagination(self, mock_get):
        page1 = _fake_response(
            200,
            [{"sha": "1"}],
            links={"next": {"url": "https://api.github.com/repos/o/r/commits?page=2"}},
        )
        page2 = _fake_response(200, [{"sha": "2"}])
        mock_get.side_effect = [page1, page2]

        commits = github_api.list_commits("tok", "octocat/repo", "2026-01-01T00:00:00Z")

        self.assertEqual([c["sha"] for c in commits], ["1", "2"])

    @mock.patch("gh_dashboard.github_api.requests.get")
    def test_raises_github_error_on_bad_status(self, mock_get):
        mock_get.return_value = _fake_response(500)
        with self.assertRaises(github_api.GitHubError):
            github_api.list_commits("tok", "octocat/repo", "2026-01-01T00:00:00Z")


class RecentActivityTests(unittest.TestCase):
    def setUp(self):
        super().setUp()
        patcher = mock.patch("gh_dashboard.github_api.verify_token")
        self.mock_verify = patcher.start()
        self.addCleanup(patcher.stop)
        self.mock_verify.return_value = {"login": "octocat"}

        patcher = mock.patch("gh_dashboard.github_api.list_repos")
        self.mock_list_repos = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = mock.patch("gh_dashboard.github_api.list_commits")
        self.mock_list_commits = patcher.start()
        self.addCleanup(patcher.stop)

    def test_skips_repos_not_pushed_to_within_the_window(self):
        self.mock_list_repos.return_value = [
            {"full_name": "octocat/recent", "pushed_at": "2026-09-01T00:00:00Z"},
            {"full_name": "octocat/ancient", "pushed_at": "2000-01-01T00:00:00Z"},
        ]
        self.mock_list_commits.return_value = []

        github_api.recent_activity("tok", days=30)

        self.mock_list_commits.assert_called_once_with(
            "tok", "octocat/recent", mock.ANY, author="octocat"
        )

    def test_each_commit_is_tagged_with_its_repo(self):
        self.mock_list_repos.return_value = [
            {"full_name": "octocat/repo", "pushed_at": "2026-09-01T00:00:00Z"},
        ]
        self.mock_list_commits.return_value = [{"sha": "abc"}]

        activity = github_api.recent_activity("tok", days=30)

        self.assertEqual(activity, [{"sha": "abc", "repo": "octocat/repo"}])

    def test_a_repo_with_no_pushed_at_is_skipped(self):
        self.mock_list_repos.return_value = [{"full_name": "octocat/weird"}]

        activity = github_api.recent_activity("tok", days=30)

        self.assertEqual(activity, [])
        self.mock_list_commits.assert_not_called()


if __name__ == "__main__":
    unittest.main()
