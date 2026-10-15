# Copyright (c) 2026 DrPlaga. Licencia MIT (ver LICENSE).

from pathlib import Path

from vpn_browser.paths import get_paths


def test_paths_use_xdg_locations(tmp_path: Path) -> None:
    env = {
        "HOME": str(tmp_path / "home"),
        "XDG_CONFIG_HOME": str(tmp_path / "config"),
        "XDG_DATA_HOME": str(tmp_path / "data"),
    }
    paths = get_paths(env)
    assert paths.config_dir == tmp_path / "config" / "vpn-browser"
    assert paths.data_dir == tmp_path / "data" / "vpn-browser"
    assert paths.secrets_dir == paths.config_dir / "secrets"
    assert paths.wireguard_import_dir == paths.config_dir / "wireguard"
    assert paths.compose_override_file == paths.config_dir / "compose.override.yaml"
    assert paths.wireguard_private_key_file == paths.secrets_dir / "wireguard_private_key"
    assert paths.openvpn_user_file == paths.secrets_dir / "openvpn_user"
    assert paths.openvpn_password_file == paths.secrets_dir / "openvpn_password"
    assert paths.ephemeral_browser_profile_dir == paths.data_dir / "ephemeral-browser-profile"


def test_paths_fall_back_to_home(tmp_path: Path) -> None:
    paths = get_paths({"HOME": str(tmp_path)})
    assert paths.config_dir == tmp_path / ".config" / "vpn-browser"
    assert (
        paths.browser_profile_dir
        == tmp_path / ".local" / "share" / "vpn-browser" / "browser-profile"
    )


def test_paths_can_use_project_local_runtime_dirs(tmp_path: Path) -> None:
    paths = get_paths(
        {
            "HOME": str(tmp_path / "home"),
            "VPN_BROWSER_CONFIG_DIR": str(tmp_path / "project" / "config" / "vpn"),
            "VPN_BROWSER_DATA_DIR": str(tmp_path / "project" / "config" / "vpn" / "data"),
        }
    )
    assert paths.config_dir == tmp_path / "project" / "config" / "vpn"
    assert paths.data_dir == tmp_path / "project" / "config" / "vpn" / "data"
    assert paths.settings_file == paths.config_dir / "settings.json"
    assert paths.wireguard_import_dir == paths.config_dir / "wireguard"
    assert (
        paths.wireguard_private_key_file
        == paths.config_dir / "secrets" / "wireguard_private_key"
    )
    assert paths.browser_profile_dir == paths.data_dir / "browser-profile"
