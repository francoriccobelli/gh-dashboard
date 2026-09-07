# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with
code in this repository.

## Project state

All three commands are implemented: `auth` stores a verified token, `summary`
prints a commit count and per-repo breakdown, `streak` prints the current and
longest run of consecutive days with a commit. `summary`/`streak` both accept
an optional `--days` flag (defaults 30 / 90) and are bounded by that window —
a streak longer than it gets undercounted, which is a documented trade-off,
not a bug (see `activity.compute_streak`'s docstring).

## Commands

```bash
python -m unittest discover -s tests -v     # full suite, stdlib only
python -m gh_dashboard.cli --help           # run without installing
pip install -e ".[dev]"                     # puts `gh-dashboard` on PATH
```

`-s tests` matters: `tests/` has no `__init__.py`, so adding `-t .` breaks
discovery with "Start directory is not importable".

Install into a virtualenv belonging to *this* project. Don't install it into a
sibling project's venv — `requests` landing in a stdlib-only project's
environment makes its local runs diverge from its CI.

## Architecture

Four modules, layered one way with no cycles:

```
config.py       owns ~/.gh_dashboard/config.json  (never prints, never calls the network)
    ^
github_api.py   HTTP -> plain data                (never prints, never reads the config file)
    ^
activity.py     plain data -> plain data          (no I/O at all: no files, no network, no printing)
    ^
cli.py          argparse, dispatch, printing      (opens nothing, issues no requests itself)
```

`cli.py` asks `config` for the token, hands it to `github_api`, and hands
whatever `github_api` returns to `activity` for the actual count/streak math.
Keeping that one-way is what lets each module be tested without the others:
`github_api` against a fake response, `config` against a temp path, `activity`
against plain lists of dicts, `cli` against mocks of the other three. This is
the one rule to preserve when adding features. `activity.py` exists because
that math is neither an HTTP concern nor a printing concern — it doesn't
belong bolted onto either of the modules that already have a job.

Conventions that follow from that split:

- **Handlers return exit codes.** Each `cmd_*` takes the parsed namespace and
  returns an `int` (0 = success) rather than calling `sys.exit`. Tests call
  them directly and assert on the return value.
- **Errors go to stderr, results to stdout.** `main()` is the single place
  that turns a `GitHubError` (bad token, rate limit, network), an `OSError`,
  or a `ValueError` (a corrupt config file) into a one-line message and exit
  1 — so no handler needs its own try/except and no user sees a traceback.
- **Not authenticated is a handled case, not a crash.** `summary`/`streak`
  call `cli._token_or_hint()` first; a `None` means `auth` hasn't been run,
  and the handler prints a hint and returns 1 itself, before anything network-
  or `activity`-related runs.
- **`build_parser()` is split out from `main()`** so tests can inspect the
  parser and check `--help` without running a command.
- **`main(argv=None)` takes argv as a parameter**, defaulting to `sys.argv[1:]`.
  That is what lets tests drive `main()` directly instead of patching `sys.argv`.
- **`config_file()` is indirection on purpose.** Nothing should hard-code
  `CONFIG_FILE`. Resolving the path on every call is what will let tests
  redirect it, and what a future `--config-file` flag will hook into.

## Dependencies

One runtime dependency, `requests`, because talking to the GitHub REST API is
the whole point. That is a deliberate exception, not an opening — reach for the
standard library for everything else, and add a second dependency only when it
really earns its place. Requires Python 3.10+ (the code uses `X | None`
annotations and `from __future__ import annotations`).

## Testing

The token lives at `~/.gh_dashboard/config.json`, in the developer's own home
directory. Any test that touches `config.save_token`/`load_token`/`clear_token`
must subclass `tests/_helpers.ConfigFileTestCase`, which redirects
`config.CONFIG_FILE` to a temp path for the duration of the test — never let a
test reach the real file. `tests/test_config.py` and the auth/summary/streak
tests in `tests/test_cli.py` all do this; anything new that stores or reads
the token should too.

**Never put a real token in a test, a fixture, or a commit.**

Every `github_api.py` test mocks `requests.get` (or, for `recent_activity`,
mocks `verify_token`/`list_repos`/`list_commits` at the module level to test
its orchestration in isolation) — no test makes a real GitHub call.
`activity.py`'s tests need neither mock nor temp path; it's pure functions
over plain lists of dicts.

## Writing a new command

1. Add a subparser in `build_parser()` and a `cmd_*` handler beside the others.
2. Read the token via `cli._token_or_hint()` (handles the not-authenticated
   case), fetch through `github_api`, aggregate through `activity` if the
   command needs count/streak-style math, then print. The handler itself
   opens no file and makes no request.
3. Let exceptions propagate; `main()` renders them.
4. Test it on the exit code and the parsed arguments, not only on printed
   output.
