# Author: DrPlaga

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from vpn_browser.constants import APP_NAME

PRIVATE_DIR_MODE = 0o700
PRIVATE_FILE_MODE = 0o600


@dataclass(frozen=True)
class ProjectPaths:
    config_dir: Path
    data_dir: Path
    secrets_dir: Path
    wireguard_import_dir: Path
    settings_file: Path
    compose_override_file: Path
    wireguard_private_key_file: Path
    openvpn_user_file: Path
    openvpn_password_file: Path
    browser_profile_dir: Path
    ephemeral_browser_profile_dir: Path


def _xdg_dir(env: os._Environ[str] | dict[str, str], key: str, fallback: Path) -> Path:
    value = env.get(key)
    if value:
        return Path(value).expanduser()
    return fallback


def get_paths(env: os._Environ[str] | dict[str, str] | None = None) -> ProjectPaths:
    env = env if env is not None else os.environ
    home = Path(env.get("HOME", str(Path.home()))).expanduser()
    config_home = _xdg_dir(env, "XDG_CONFIG_HOME", home / ".config")
    data_home = _xdg_dir(env, "XDG_DATA_HOME", home / ".local" / "share")

    config_dir = _xdg_dir(env, "VPN_BROWSER_CONFIG_DIR", config_home / APP_NAME)
    data_dir = _xdg_dir(env, "VPN_BROWSER_DATA_DIR", data_home / APP_NAME)
    secrets_dir = config_dir / "secrets"
    wireguard_import_dir = config_dir / "wireguard"
    return ProjectPaths(
        config_dir=config_dir,
        data_dir=data_dir,
        secrets_dir=secrets_dir,
        wireguard_import_dir=wireguard_import_dir,
        settings_file=config_dir / "settings.json",
        compose_override_file=config_dir / "compose.override.yaml",
        wireguard_private_key_file=secrets_dir / "wireguard_private_key",
        openvpn_user_file=secrets_dir / "openvpn_user",
        openvpn_password_file=secrets_dir / "openvpn_password",
        browser_profile_dir=data_dir / "browser-profile",
        ephemeral_browser_profile_dir=data_dir / "ephemeral-browser-profile",
    )


def ensure_private_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    path.chmod(PRIVATE_DIR_MODE)


def ensure_base_directories(paths: ProjectPaths) -> None:
    ensure_private_dir(paths.config_dir)
    ensure_private_dir(paths.secrets_dir)
    ensure_private_dir(paths.wireguard_import_dir)
    ensure_private_dir(paths.data_dir)
