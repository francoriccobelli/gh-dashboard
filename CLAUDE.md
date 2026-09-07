# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with
code in this repository.

## Project state

Scaffold only. All three commands (`auth`, `summary`, `streak`) parse and
dispatch, but each prints `not implemented yet` and returns 0. `config.py` and
`github_api.py` are docstrings over `NotImplementedError` — they record the
intended shape and nothing else. No HTTP request has been written yet, and
`requests` is declared as a dependency but not yet imported anywhere.

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

Three modules, layered one way with no cycles:

```
config.py       owns ~/.gh_dashboard/config.json  (never prints, never calls the network)
    ^
github_api.py   HTTP -> plain data                (never prints, never reads the config file)
    ^
cli.py          argparse, dispatch, printing      (opens nothing, issues no requests itself)
```

`cli.py` asks `config` for the token and hands it to `github_api`. Keeping that
one-way is what lets each module be tested without the others: `github_api`
against a fake response, `config` against a temp path, `cli` against neither.
This is the one rule to preserve when adding features.

Conventions that follow from that split:

- **Handlers return exit codes.** Each `cmd_*` takes the parsed namespace and
  returns an `int` (0 = success) rather than calling `sys.exit`. Tests call
  them directly and assert on the return value.
- **Errors go to stderr, results to stdout.** `main()` is the single place that
  will turn a `GitHubError` (bad token, rate limit, network) or an `OSError`
  into a one-line message and exit 1 — so no handler needs its own try/except
  and no user sees a traceback.
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

## Testing: the rule to establish before it bites

The token will live at `~/.gh_dashboard/config.json`, in the developer's own
home directory. The moment `config.save_token` actually writes, any test that
reaches it must redirect the path first — through `config_file()` — or the
suite will overwrite the real token of whoever runs it.

Write that base `TestCase` when the first storage test is written, not after.
`tests/test_cli.py` currently touches no disk, which is why it needs nothing yet.

**Never put a real token in a test, a fixture, or a commit.**

## Writing a new command

1. Add a subparser in `build_parser()` and a `cmd_*` handler beside the others.
2. Read the token via `config`, fetch through `github_api`, print what comes
   back. The handler itself opens no file and makes no request.
3. Let exceptions propagate; `main()` renders them.
4. Test it on the exit code and the parsed arguments, not only on printed
   output.
