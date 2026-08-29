"""Smoke test that the tmp_samantha_home fixture works."""

from __future__ import annotations

from pathlib import Path

from samantha.core import config as config_mod


def test_fixture_redirects_default_config_dir(tmp_samantha_home: Path) -> None:
    assert config_mod.DEFAULT_CONFIG_DIR == tmp_samantha_home
    assert tmp_samantha_home.exists()
    assert (tmp_samantha_home / ".state").exists()
    assert (tmp_samantha_home / ".state" / "models").exists()


def test_fixture_redirects_config_path(tmp_samantha_home: Path) -> None:
    assert config_mod.DEFAULT_CONFIG_PATH == tmp_samantha_home / "config.toml"
