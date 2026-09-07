"""Local configuration: the sole owner of the on-disk config file.

This module owns the config file at ``~/.gh_dashboard/config.json`` — its path,
its format, and any future migrations. Nothing else opens it. It never prints
and never calls the network; it takes data and returns data, so it can be
tested without a CLI or a live API.

The file holds the user's GitHub personal access token, which is a secret, so
it is written with owner-only permissions (``0o600``) and lives outside any
repository.

Nothing here is implemented yet — the functions below record the intended
shape.
"""

from __future__ import annotations

from pathlib import Path

CONFIG_DIR = Path.home() / ".gh_dashboard"
CONFIG_FILE = CONFIG_DIR / "config.json"


def config_file() -> Path:
    """Return the path of the config file, resolved on every call.

    An accessor rather than a bare constant so the location can be redirected
    at *call* time — by tests, or by a future ``--config-file`` flag — without
    anything having to reach for the module constant.
    """
    raise NotImplementedError


def save_token(token: str) -> None:
    """Store ``token`` in the config file, creating the directory if needed.

    Writes the whole file, not an append. Because the payload is a secret, the
    file is created with mode ``0o600`` (owner read/write only) and the write
    is atomic: a temp file in the same directory, then ``os.replace``.
    """
    raise NotImplementedError


def load_token() -> str | None:
    """Return the stored token, or ``None`` when none has been saved.

    A missing file is not an error — it means the user has not run ``auth``
    yet. A file that exists but cannot be parsed *is* an error, and raises
    ``ValueError`` for the CLI to render.
    """
    raise NotImplementedError


def clear_token() -> None:
    """Remove any stored token. Succeeds quietly when there is nothing to remove."""
    raise NotImplementedError
