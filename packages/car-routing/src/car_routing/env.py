"""Minimal .env loading, so a key can live in a file instead of a shell.

Deliberately dependency-free and deliberately dumb: ``KEY=value`` lines,
``#`` comments, optional ``export`` prefix, optional surrounding quotes. If you
want interpolation or multiline values, use python-dotenv instead.
"""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_ENV_FILE = ".env"


def parse_env(text: str) -> dict[str, str]:
    """Read ``KEY=value`` pairs out of .env-style text."""
    values: dict[str, str] = {}

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        if "=" not in line:
            continue

        name, _, raw = line.partition("=")
        name = name.strip()
        if not name:
            continue

        value = raw.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[name] = value

    return values


def load_env(
    path: str | os.PathLike[str] = DEFAULT_ENV_FILE,
    *,
    override: bool = False,
) -> dict[str, str]:
    """Load ``path`` into ``os.environ`` and return what was applied.

    Existing environment variables win unless ``override`` is set, so a real
    shell export still beats the file. A missing file is not an error -- it
    returns ``{}``, which keeps this safe to call unconditionally.
    """
    env_path = Path(path)
    if not env_path.is_file():
        return {}

    applied: dict[str, str] = {}
    for name, value in parse_env(env_path.read_text(encoding="utf-8")).items():
        if override or name not in os.environ:
            os.environ[name] = value
            applied[name] = value

    return applied
