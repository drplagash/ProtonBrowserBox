# Copyright (c) 2026 DrPlaga. Licencia MIT (ver LICENSE).

import json
import stat
from pathlib import Path

import pytest

from vpn_browser.config import (
    ConfigError,
    Settings,
    load_settings,
    save_settings,
    settings_from_dict,
)
from vpn_browser.paths import get_paths


def test_default_settings_are_valid() -> None:
    settings = Settings.default()
    assert settings.schema_version == 1
    assert settings.memory_profile == "normal"
    assert settings.memory_limit_mb == 2048
    assert settings.disk_budget_mb == 4096


def test_save_and_load_settings(tmp_path: Path) -> None:
    paths = get_paths({"HOME": str(tmp_path)})
    settings = Settings.default()
    save_settings(paths, settings)
    assert load_settings(paths) == settings
    mode = stat.S_IMODE(paths.settings_file.stat().st_mode)
    assert mode == 0o600


def test_load_missing_settings_returns_none(tmp_path: Path) -> None:
    assert load_settings(get_paths({"HOME": str(tmp_path)})) is None


def test_corrupt_settings_fail(tmp_path: Path) -> None:
    paths = get_paths({"HOME": str(tmp_path)})
    paths.config_dir.mkdir(parents=True)
    paths.settings_file.write_text("{not json", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_settings(paths)


def test_unknown_schema_fails() -> None:
    with pytest.raises(ConfigError):
        settings_from_dict({"schema_version": 999})


def test_invalid_port_fails() -> None:
    data = json.loads(json.dumps(Settings.default().__dict__))
    data["web_port"] = 80
    with pytest.raises(ConfigError):
        settings_from_dict(data)


def test_manual_country_requires_country() -> None:
    data = json.loads(json.dumps(Settings.default().__dict__))
    data["country_mode"] = "manual"
    data["country"] = None
    with pytest.raises(ConfigError):
        settings_from_dict(data)


def test_manual_country_rejects_unsafe_characters() -> None:
    data = json.loads(json.dumps(Settings.default().__dict__))
    data["country_mode"] = "manual"
    data["country"] = "United States\nBAD=1"
    with pytest.raises(ConfigError):
        settings_from_dict(data)


def test_wireguard_endpoint_port_rejects_invalid_values() -> None:
    data = json.loads(json.dumps(Settings.default().__dict__))
    data["wireguard_endpoint_port"] = 70000
    with pytest.raises(ConfigError):
        settings_from_dict(data)


def test_wireguard_implementation_rejects_invalid_values() -> None:
    data = json.loads(json.dumps(Settings.default().__dict__))
    data["wireguard_implementation"] = "bad"
    with pytest.raises(ConfigError):
        settings_from_dict(data)


def test_provider_mode_rejects_invalid_values() -> None:
    data = json.loads(json.dumps(Settings.default().__dict__))
    data["provider_mode"] = "bad"
    with pytest.raises(ConfigError):
        settings_from_dict(data)


def test_custom_provider_requires_wireguard_metadata() -> None:
    data = json.loads(json.dumps(Settings.default().__dict__))
    data["provider_mode"] = "custom"
    with pytest.raises(ConfigError):
        settings_from_dict(data)


def test_custom_provider_requires_endpoint_ip() -> None:
    data = json.loads(json.dumps(Settings.default().__dict__))
    data["provider_mode"] = "custom"
    data["wireguard_public_key"] = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    data["wireguard_endpoint_ip"] = "vpn.example.com"
    data["wireguard_endpoint_port"] = 51820
    data["wireguard_addresses"] = ["10.2.0.2/32"]
    with pytest.raises(ConfigError):
        settings_from_dict(data)


def test_wireguard_mtu_rejects_invalid_values() -> None:
    data = json.loads(json.dumps(Settings.default().__dict__))
    data["wireguard_mtu"] = 100
    with pytest.raises(ConfigError):
        settings_from_dict(data)
