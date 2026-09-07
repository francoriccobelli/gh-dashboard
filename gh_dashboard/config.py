"""Local configuration: the sole owner of the on-disk config file.

This module owns the config file at ``~/.gh_dashboard/config.json`` — its path,
its format, and any future migrations. Nothing else opens it. It never prints
and never calls the network; it takes data and returns data, so it can be
tested without a CLI or a live API.

The file holds the user's GitHub personal access token, which is a secret, so
it is written with owner-only permissions (``0o600``) and lives outside any
repository.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

CONFIG_DIR = Path.home() / ".gh_dashboard"
CONFIG_FILE = CONFIG_DIR / "config.json"


def config_file() -> Path:
    """Return the path of the config file, resolved on every call.

    An accessor rather than a bare constant so the location can be redirected
    at *call* time — by tests, or by a future ``--config-file`` flag — without
    anything having to reach for the module constant. Reading ``CONFIG_FILE``
    fresh on every call (rather than caching it) is what makes patching that
    module attribute in tests actually take effect.
    """
    return CONFIG_FILE


def save_token(token: str) -> None:
    """Store ``token`` in the config file, creating the directory if needed.

    Writes the whole file, not an append. The write is atomic — a temp file
    in the same directory (so the final rename stays on one filesystem), made
    owner-only before it lands at the real path via ``os.replace``.

    Note: on Windows, ``os.chmod`` only toggles the read-only attribute — it
    does not restrict access the way ``0o600`` does on POSIX. The call still
    happens, since it's correct on POSIX (including CI), but on Windows the
    directory's own ACL is the real protection, not this permission bit.
    """
    token = token.strip()
    if not token:
        raise ValueError("token must not be empty")

    path = config_file()
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=".config-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"token": token}, f)
        os.chmod(tmp_name, 0o600)
        os.replace(tmp_name, path)
    except BaseException:
        os.unlink(tmp_name)
        raise


def load_token() -> str | None:
    """Return the stored token, or ``None`` when none has been saved.

    A missing file is not an error — it means the user has not run ``auth``
    yet. A file that exists but cannot be parsed, or doesn't contain a
    ``"token"`` string, raises ``ValueError`` for the CLI to render.
    """
    path = config_file()
    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        token = data["token"]
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        raise ValueError(f"{path} is not a valid gh-dashboard config file") from e

    if not isinstance(token, str):
        raise ValueError(f"{path} is not a valid gh-dashboard config file")
    return token


def clear_token() -> None:
    """Remove any stored token. Succeeds quietly when there is nothing to remove."""
    config_file().unlink(missing_ok=True)
