from __future__ import annotations

import importlib
import sys

from importlib import metadata

import salsa_milk


def test_get_version_matches_dunder():
    assert salsa_milk.get_version() == salsa_milk.__version__
    assert isinstance(salsa_milk.__version__, str)


def test_version_metadata_override(monkeypatch):
    original = salsa_milk
    monkeypatch.delitem(sys.modules, "salsa_milk", raising=False)

    def fake_version(name: str) -> str:
        assert name == "salsa-milk"
        return "9.9.9"

    monkeypatch.setattr(metadata, "version", fake_version)
    reloaded = importlib.import_module("salsa_milk")
    assert reloaded.get_version() == "9.9.9"
    assert reloaded.__version__ == "9.9.9"
    sys.modules["salsa_milk"] = original
