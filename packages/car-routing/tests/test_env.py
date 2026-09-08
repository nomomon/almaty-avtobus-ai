"""Tests for .env loading and key resolution from a file."""

from __future__ import annotations

import os
import pathlib
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from car_routing import load_env, parse_env, resolve_key  # noqa: E402
from car_routing.client import CarRoutingError  # noqa: E402

SAMPLE = """
# a comment
TWOGIS_ROUTING_KEY=abc-123

export QUOTED="quoted-value"
SINGLE='single-value'
SPACED  =  padded
EMPTY=
NOT_AN_ASSIGNMENT
=novalue
WITH_EQUALS=a=b=c
"""


def test_parse_env_handles_the_usual_shapes():
    parsed = parse_env(SAMPLE)

    assert parsed["TWOGIS_ROUTING_KEY"] == "abc-123"
    assert parsed["QUOTED"] == "quoted-value"  # export prefix + double quotes
    assert parsed["SINGLE"] == "single-value"
    assert parsed["SPACED"] == "padded"  # whitespace around name and value
    assert parsed["EMPTY"] == ""
    assert parsed["WITH_EQUALS"] == "a=b=c"  # only the first = splits
    assert "NOT_AN_ASSIGNMENT" not in parsed
    assert "" not in parsed  # a nameless "=novalue" line is dropped


def test_load_env_populates_environ(tmp_path, monkeypatch):
    monkeypatch.delenv("TWOGIS_ROUTING_KEY", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("TWOGIS_ROUTING_KEY=from-file\n")

    applied = load_env(env_file)

    assert applied == {"TWOGIS_ROUTING_KEY": "from-file"}
    assert os.environ["TWOGIS_ROUTING_KEY"] == "from-file"
    assert resolve_key() == "from-file"


def test_real_environment_beats_the_file(tmp_path, monkeypatch):
    monkeypatch.setenv("TWOGIS_ROUTING_KEY", "from-shell")
    env_file = tmp_path / ".env"
    env_file.write_text("TWOGIS_ROUTING_KEY=from-file\n")

    assert load_env(env_file) == {}
    assert os.environ["TWOGIS_ROUTING_KEY"] == "from-shell"


def test_override_flips_the_precedence(tmp_path, monkeypatch):
    monkeypatch.setenv("TWOGIS_ROUTING_KEY", "from-shell")
    env_file = tmp_path / ".env"
    env_file.write_text("TWOGIS_ROUTING_KEY=from-file\n")

    assert load_env(env_file, override=True) == {"TWOGIS_ROUTING_KEY": "from-file"}
    assert os.environ["TWOGIS_ROUTING_KEY"] == "from-file"


def test_missing_file_is_not_an_error(tmp_path, monkeypatch):
    for name in ("TWOGIS_ROUTING_KEY", "TWOGIS_API_KEY", "2GIS_API_KEY"):
        monkeypatch.delenv(name, raising=False)

    assert load_env(tmp_path / "nope.env") == {}
    with pytest.raises(CarRoutingError, match="No 2GIS API key"):
        resolve_key()


def test_dotenv_is_gitignored():
    """A key in .env must not be committable."""
    here = pathlib.Path(__file__).resolve()
    gitignore = next(
        (p / ".gitignore" for p in here.parents if (p / ".gitignore").is_file()), None
    )
    assert gitignore is not None, "no .gitignore found above the tests"
    assert ".env" in gitignore.read_text().split()
