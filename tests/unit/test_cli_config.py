# Copyright (c) 2026 DrPlaga. Licencia MIT (ver LICENSE).

import stat
from pathlib import Path

from vpn_browser.cli import main
from vpn_browser.config import load_settings
from vpn_browser.paths import get_paths

VALID_KEY = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="


def test_config_wizard_imports_only_secret(monkeypatch, tmp_path: Path, capsys) -> None:
    conf = tmp_path / "proton.conf"
    conf.write_text(f"[Interface]\nPrivateKey = {VALID_KEY}\n", encoding="utf-8")
    answers = iter(["2", "1", "5800", "1920x1080", str(conf)])
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.delenv("VPN_BROWSER_CONFIG_DIR", raising=False)
    monkeypatch.delenv("VPN_BROWSER_DATA_DIR", raising=False)
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))

    assert main(["config"]) == 0
    output = capsys.readouterr().out
    paths = get_paths({"HOME": str(tmp_path)})
    assert paths.settings_file.exists()
    assert paths.wireguard_private_key_file.exists()
    assert VALID_KEY not in output
    assert "PrivateKey: [REDACTED]" in output
    assert "proton.conf" not in paths.settings_file.read_text(encoding="utf-8")
    assert load_settings(paths).provider_mode == "proton"


def test_config_wizard_auto_imports_single_project_conf(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    paths = get_paths(
        {
            "HOME": str(tmp_path / "home"),
            "VPN_BROWSER_CONFIG_DIR": str(tmp_path / "project" / "config" / "vpn"),
            "VPN_BROWSER_DATA_DIR": str(tmp_path / "project" / "config" / "vpn" / "data"),
        }
    )
    paths.wireguard_import_dir.mkdir(parents=True)
    conf = paths.wireguard_import_dir / "proton.conf"
    conf.write_text(f"[Interface]\nPrivateKey = {VALID_KEY}\n", encoding="utf-8")
    conf.chmod(0o644)
    answers = iter(["2", "1", "5800", "1920x1080"])
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("VPN_BROWSER_CONFIG_DIR", str(paths.config_dir))
    monkeypatch.setenv("VPN_BROWSER_DATA_DIR", str(paths.data_dir))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))

    assert main(["config"]) == 0

    output = capsys.readouterr().out
    assert f"Using: {conf}" in output
    assert paths.settings_file.exists()
    assert paths.wireguard_private_key_file.exists()
    assert stat.S_IMODE(conf.stat().st_mode) == 0o600
    assert load_settings(paths).provider_mode == "proton"


def test_config_wizard_uses_exact_config_when_peer_is_complete(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    conf = tmp_path / "proton.conf"
    conf.write_text(
        "[Interface]\n"
        f"PrivateKey = {VALID_KEY}\n"
        "Address = 10.2.0.2/32\n"
        "[Peer]\n"
        "PublicKey = AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=\n"
        "Endpoint = 95.173.217.71:51820\n",
        encoding="utf-8",
    )
    answers = iter(["2", "1", "5800", "1920x1080", str(conf)])
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.delenv("VPN_BROWSER_CONFIG_DIR", raising=False)
    monkeypatch.delenv("VPN_BROWSER_DATA_DIR", raising=False)
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))

    assert main(["config"]) == 0
    output = capsys.readouterr().out
    paths = get_paths({"HOME": str(tmp_path)})
    settings = load_settings(paths)
    assert settings.provider_mode == "custom"
    assert settings.wireguard_endpoint_ip == "95.173.217.71"
    assert "Server selection: Exact WireGuard config" in output
    assert VALID_KEY not in output


def test_openvpn_wizard_sets_resources_without_wireguard(monkeypatch, tmp_path, capsys):
    config_dir = tmp_path / "config"
    monkeypatch.setenv("VPN_BROWSER_CONFIG_DIR", str(config_dir))
    monkeypatch.setenv("VPN_BROWSER_DATA_DIR", str(tmp_path / "data"))
    answers = iter(["1", "2", "5801", "1280x720", "example-openvpn-user"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))
    monkeypatch.setattr("getpass.getpass", lambda _prompt="": "test-only-password")

    assert main(["config", "--openvpn-tcp"]) == 0

    paths = get_paths()
    settings = load_settings(paths)
    assert settings.vpn_protocol == "openvpn"
    assert settings.openvpn_protocol == "tcp"
    assert settings.openvpn_endpoint_port == 443
    assert settings.memory_limit_mb == 1024
    assert settings.disk_budget_mb == 2048
    assert settings.persistent_browser_profile is False
    assert settings.web_port == 5801
    assert settings.resolution == "1280x720"
    assert not paths.wireguard_private_key_file.exists()
    assert stat.S_IMODE(paths.openvpn_password_file.stat().st_mode) == 0o600
    output = capsys.readouterr().out
    assert "example-openvpn-user" not in output
    assert "test-only-password" not in output
