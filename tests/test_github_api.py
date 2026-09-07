"""Tests for the GitHub REST API wrapper. No real HTTP: requests.get is mocked."""

import unittest
from unittest import mock

import requests

from gh_dashboard import github_api


def _fake_response(status_code, json_data=None):
    response = mock.Mock()
    response.status_code = status_code
    response.ok = 200 <= status_code < 300
    response.json.return_value = json_data
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


if __name__ == "__main__":
    unittest.main()
