# Author: DrPlaga

from vpn_browser.cli import main
from vpn_browser.config import Settings, load_settings, save_settings
from vpn_browser.paths import get_paths
from vpn_browser.secrets import write_openvpn_credentials, write_wireguard_private_key


def _configured_home(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.delenv("VPN_BROWSER_CONFIG_DIR", raising=False)
    monkeypatch.delenv("VPN_BROWSER_DATA_DIR", raising=False)
    paths = get_paths({"HOME": str(tmp_path)})
    save_settings(paths, Settings.default())
    return paths


def test_version_outputs_version(capsys) -> None:
    assert main(["version"]) == 0
    output = capsys.readouterr().out
    assert "ProtonBrowserBox" in output
    assert "0.1.0" in output


def test_status_without_config_is_safe(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.delenv("VPN_BROWSER_CONFIG_DIR", raising=False)
    monkeypatch.delenv("VPN_BROWSER_DATA_DIR", raising=False)
    assert main(["status"]) == 0
    output = capsys.readouterr().out
    assert "Configuration: WARNING" in output
    assert "WIREGUARD_PRIVATE_KEY" not in output


def test_start_without_config_does_not_start_browser(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.delenv("VPN_BROWSER_CONFIG_DIR", raising=False)
    monkeypatch.delenv("VPN_BROWSER_DATA_DIR", raising=False)
    assert main([]) == 0
    output = capsys.readouterr().out
    assert "Browser was NOT started." in output
    assert "No fallback network is enabled." in output


def test_server_without_config_is_safe(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.delenv("VPN_BROWSER_CONFIG_DIR", raising=False)
    monkeypatch.delenv("VPN_BROWSER_DATA_DIR", raising=False)
    assert main(["server"]) == 0
    assert "not configured yet" in capsys.readouterr().out


def test_server_country_updates_settings(monkeypatch, tmp_path, capsys) -> None:
    paths = _configured_home(monkeypatch, tmp_path)

    assert main(["server", "--country", "United States"]) == 0

    settings = load_settings(paths)
    assert settings.country_mode == "manual"
    assert settings.country == "United States"
    assert settings.provider_mode == "proton"
    assert "Server selection: Proton Free / United States" in capsys.readouterr().out


def test_server_auto_clears_manual_country(monkeypatch, tmp_path, capsys) -> None:
    paths = _configured_home(monkeypatch, tmp_path)
    save_settings(
        paths,
        Settings(country_mode="manual", country="United States"),
    )

    assert main(["server", "--auto"]) == 0

    settings = load_settings(paths)
    assert settings.country_mode == "automatic"
    assert settings.country is None
    assert settings.provider_mode == "proton"
    assert "Server selection: Proton Free / automatic" in capsys.readouterr().out


def test_server_exact_uses_imported_wireguard_metadata(monkeypatch, tmp_path, capsys) -> None:
    paths = _configured_home(monkeypatch, tmp_path)
    save_settings(
        paths,
        Settings(
            provider_mode="proton",
            wireguard_endpoint_ip="95.173.217.71",
            wireguard_endpoint_port=51820,
            wireguard_public_key="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            wireguard_addresses=["10.2.0.2/32"],
        ),
    )

    assert main(["server", "--exact"]) == 0

    settings = load_settings(paths)
    assert settings.provider_mode == "custom"
    assert "Server selection: Exact imported WireGuard config" in capsys.readouterr().out


def test_server_exact_requires_imported_wireguard_metadata(monkeypatch, tmp_path, capsys) -> None:
    _configured_home(monkeypatch, tmp_path)

    assert main(["server", "--exact"]) == 1

    assert "no exact WireGuard peer metadata" in capsys.readouterr().err


def test_server_openvpn_tcp_stores_credentials(monkeypatch, tmp_path, capsys) -> None:
    paths = _configured_home(monkeypatch, tmp_path)
    monkeypatch.setattr("builtins.input", lambda _prompt="": "openvpn-user")
    monkeypatch.setattr("getpass.getpass", lambda _prompt="": "openvpn-password")

    assert main(["server", "--openvpn-tcp"]) == 0

    settings = load_settings(paths)
    assert settings.vpn_protocol == "openvpn"
    assert settings.openvpn_protocol == "tcp"
    assert settings.openvpn_endpoint_port == 443
    assert paths.openvpn_user_file.read_text(encoding="utf-8").strip() == "openvpn-user"
    assert paths.openvpn_password_file.read_text(encoding="utf-8").strip() == "openvpn-password"
    output = capsys.readouterr().out
    assert "Proton OpenVPN TCP/443" in output
    assert "openvpn-password" not in output


def test_server_openvpn_tcp_without_config_creates_default_settings(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.delenv("VPN_BROWSER_CONFIG_DIR", raising=False)
    monkeypatch.delenv("VPN_BROWSER_DATA_DIR", raising=False)
    monkeypatch.setattr("builtins.input", lambda _prompt="": "openvpn-user")
    monkeypatch.setattr("getpass.getpass", lambda _prompt="": "openvpn-password")
    paths = get_paths({"HOME": str(tmp_path)})

    assert main(["server", "--openvpn-tcp"]) == 0

    settings = load_settings(paths)
    assert settings.vpn_protocol == "openvpn"
    assert settings.provider_mode == "proton"
    assert settings.openvpn_protocol == "tcp"
    assert settings.openvpn_endpoint_port == 443
    assert settings.web_port == 5800
    assert paths.openvpn_user_file.read_text(encoding="utf-8").strip() == "openvpn-user"
    assert paths.openvpn_password_file.read_text(encoding="utf-8").strip() == "openvpn-password"
    output = capsys.readouterr().out
    assert "default settings will be created" in output
    assert "OpenVPN credentials: PASS" in output


def test_reset_requires_confirmation(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.delenv("VPN_BROWSER_CONFIG_DIR", raising=False)
    monkeypatch.delenv("VPN_BROWSER_DATA_DIR", raising=False)
    monkeypatch.setattr("builtins.input", lambda _prompt="": "no")
    assert main(["reset"]) == 0
    assert "not removed" in capsys.readouterr().out


def test_reset_removes_both_protocol_secrets_but_keeps_imports_and_profile(
    monkeypatch, tmp_path,
) -> None:
    paths = _configured_home(monkeypatch, tmp_path)
    write_openvpn_credentials(paths, "example-openvpn-user", "test-only-password")
    write_wireguard_private_key(paths, "test-only-wireguard-key")
    paths.compose_override_file.write_text("services: {}\n", encoding="utf-8")
    imported = paths.wireguard_import_dir / "proton.conf"
    imported.write_text("test-only-import", encoding="utf-8")
    paths.browser_profile_dir.mkdir(parents=True)
    profile = paths.browser_profile_dir / "prefs.js"
    profile.write_text("test-only-profile", encoding="utf-8")
    monkeypatch.setattr("builtins.input", lambda _prompt="": "DELETE CONFIG")

    assert main(["reset"]) == 0

    assert not paths.settings_file.exists()
    assert not paths.compose_override_file.exists()
    assert not paths.wireguard_private_key_file.exists()
    assert not paths.openvpn_user_file.exists()
    assert not paths.openvpn_password_file.exists()
    assert imported.exists()
    assert profile.exists()


def test_logs_redact_local_secret_values_in_free_text(monkeypatch, tmp_path, capsys):
    from subprocess import CompletedProcess

    paths = _configured_home(monkeypatch, tmp_path)
    write_openvpn_credentials(paths, "example-openvpn-user", "test-only-password")
    write_wireguard_private_key(paths, "test-only-wireguard-key")
    monkeypatch.setattr(
        "vpn_browser.cli.run_compose",
        lambda *_args, **_kwargs: CompletedProcess(
            [], 0,
            stdout=(
                "user example-openvpn-user password test-only-password "
                "key test-only-wireguard-key"
            ),
        ),
    )

    assert main(["logs"]) == 0

    output = capsys.readouterr().out
    assert "example-openvpn-user" not in output
    assert "test-only-password" not in output
    assert "test-only-wireguard-key" not in output
    assert output.count("[REDACTED]") == 3
