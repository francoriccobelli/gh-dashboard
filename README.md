# gh-dashboard

CLI tool that summarizes your GitHub activity — built to learn API integration with Claude Code.

## Install

```bash
git clone https://github.com/francoriccobelli/gh-dashboard.git
cd gh-dashboard
python -m venv .venv
.venv\Scripts\Activate.ps1     # Windows PowerShell; use .venv/bin/activate on macOS/Linux
pip install -e ".[dev]"
```

## Get a token

`gh-dashboard` needs a GitHub personal access token. Create a fine-grained one at
[github.com/settings/personal-access-tokens/new](https://github.com/settings/personal-access-tokens/new):

- **Repository access**: "All repositories" (or "Only select repositories" if you'd rather list them explicitly)
- **Permissions → Repository permissions → Contents**: Read-only (Metadata: Read-only comes along automatically — GitHub requires it as soon as any other repository permission is granted)

Nothing else is needed — no Account permissions, no write access anywhere. `auth` alone would work with an even more minimal token (it only confirms your identity), but `summary`/`streak` need Contents access to read commits, so it's worth setting up once with the scope above.

## Usage

### `gh-dashboard auth <token>`

Verifies the token against GitHub and stores it locally for the other commands.

```
$ gh-dashboard auth ghp_xxxxxxxxxxxxxxxxxxxx
Authenticated as francoriccobelli
```

### `gh-dashboard summary [--days N]`

Commit count and per-repo breakdown over the last `N` days (default 30).

```
$ gh-dashboard summary
Last 30 days: 1 commit across 1 repository
  francoriccobelli/gh-dashboard  1

$ gh-dashboard summary --days 7
Last 7 days: 1 commit across 1 repository
  francoriccobelli/gh-dashboard  1
```

### `gh-dashboard streak [--days N]`

Your current and longest run of consecutive days with a commit, over the last `N` days (default 90).

```
$ gh-dashboard streak
Current streak: 1 day
Longest streak in the last 90 days: 1 day
```

A streak longer than the `--days` window gets undercounted — this reads GitHub's REST commits API across your repositories, not the GraphQL contribution-calendar endpoint that powers the green squares on your profile, so it won't always match that number exactly.

### `gh-dashboard logout`

Removes the stored token.

```
$ gh-dashboard logout
Logged out.
```

## Token storage

The token lives at `~/.gh_dashboard/config.json`, outside this repository. On POSIX it's written with owner-only (`0600`) permissions; on Windows that permission bit isn't meaningful, so your user account's own access to its home directory is what actually protects it. Never commit this file or paste a token into anything tracked by git — `gh-dashboard auth` is the only place a token should ever be typed.

## Development

```bash
pytest -q
# or: python -m unittest discover -s tests -v
```

See [CLAUDE.md](CLAUDE.md) for the module layout and conventions this project follows.
