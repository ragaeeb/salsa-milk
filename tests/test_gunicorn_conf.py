from __future__ import annotations

import importlib.util
from pathlib import Path


def load_conf_module(tmp_name: str = "gunicorn_conf_test"):
    spec = importlib.util.spec_from_file_location(tmp_name, Path("gunicorn.conf.py"))
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)  # type: ignore[assignment]
    return module


def test_int_env_parsing(monkeypatch, tmp_path):
    module = load_conf_module()
    assert module._int_env("MISSING", 3) == 3

    monkeypatch.setenv("TEST_VALUE", "5")
    assert module._int_env("TEST_VALUE", 1, minimum=10) == 10

    monkeypatch.setenv("TEST_VALUE", "")
    assert module._int_env("TEST_VALUE", 7) == 7

    monkeypatch.setenv("TEST_VALUE", "None")
    assert module._int_env("TEST_VALUE", 9, allow_none=True) is None

    monkeypatch.setenv("TEST_VALUE", "invalid")
    assert module._int_env("TEST_VALUE", 2) == 2


def test_max_requests_and_worker_tmp_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("WEB_MAX_REQUESTS", "-5")
    monkeypatch.setenv("WORKER_TMP_DIR", str(tmp_path / "workers"))
    (tmp_path / "workers").mkdir()
    module = load_conf_module("gunicorn_conf_custom")
    assert module.max_requests is None
    assert module.worker_tmp_dir == str(tmp_path / "workers")
