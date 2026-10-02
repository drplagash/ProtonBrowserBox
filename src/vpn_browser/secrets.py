# Author: DrPlaga

from __future__ import annotations

import stat
from dataclasses import dataclass
from pathlib import Path

from vpn_browser.paths import (
    PRIVATE_DIR_MODE,
    PRIVATE_FILE_MODE,
    ProjectPaths,
    ensure_base_directories,
)


class SecretError(RuntimeError):
    pass


@dataclass(frozen=True)
class PermissionCheck:
    path: Path
    expected_mode: int
    actual_mode: int | None
    status: str
    detail: str


def _mode(path: Path) -> int | None:
    if not path.exists():
        return None
    return stat.S_IMODE(path.stat().st_mode)


def write_wireguard_private_key(paths: ProjectPaths, private_key: str) -> None:
    if not private_key.strip():
        raise SecretError("WireGuard private key is empty.")
    ensure_base_directories(paths)
    tmp_file = paths.wireguard_private_key_file.with_suffix(".tmp")
    tmp_file.write_text(private_key.strip() + "\n", encoding="utf-8")
    tmp_file.chmod(PRIVATE_FILE_MODE)
    tmp_file.replace(paths.wireguard_private_key_file)
    paths.wireguard_private_key_file.chmod(PRIVATE_FILE_MODE)


def _write_secret_file(path: Path, value: str, label: str) -> None:
    if not value.strip():
        raise SecretError(f"{label} is empty.")
    tmp_file = path.with_suffix(".tmp")
    tmp_file.write_text(value.strip() + "\n", encoding="utf-8")
    tmp_file.chmod(PRIVATE_FILE_MODE)
    tmp_file.replace(path)
    path.chmod(PRIVATE_FILE_MODE)


def write_openvpn_credentials(paths: ProjectPaths, username: str, password: str) -> None:
    ensure_base_directories(paths)
    _write_secret_file(paths.openvpn_user_file, username, "OpenVPN username")
    _write_secret_file(paths.openvpn_password_file, password, "OpenVPN password")


def check_secret_permissions(paths: ProjectPaths) -> list[PermissionCheck]:
    checks = [
        (paths.config_dir, PRIVATE_DIR_MODE, "config directory"),
        (paths.secrets_dir, PRIVATE_DIR_MODE, "secrets directory"),
    ]
    if paths.wireguard_private_key_file.exists():
        checks.append(
            (paths.wireguard_private_key_file, PRIVATE_FILE_MODE, "WireGuard private key")
        )
    if paths.openvpn_user_file.exists():
        checks.append((paths.openvpn_user_file, PRIVATE_FILE_MODE, "OpenVPN username"))
    if paths.openvpn_password_file.exists():
        checks.append((paths.openvpn_password_file, PRIVATE_FILE_MODE, "OpenVPN password"))
    results: list[PermissionCheck] = []
    for path, expected, label in checks:
        actual = _mode(path)
        if actual is None:
            results.append(PermissionCheck(path, expected, actual, "WARNING", f"{label} missing"))
        elif actual == expected:
            results.append(
                PermissionCheck(path, expected, actual, "PASS", f"{label} permissions OK")
            )
        else:
            results.append(
                PermissionCheck(
                    path,
                    expected,
                    actual,
                    "WARNING",
                    f"{label} permissions are {actual:04o}, expected {expected:04o}",
                )
            )
    return results


def fix_secret_permissions(paths: ProjectPaths) -> None:
    if paths.config_dir.exists():
        paths.config_dir.chmod(PRIVATE_DIR_MODE)
    if paths.secrets_dir.exists():
        paths.secrets_dir.chmod(PRIVATE_DIR_MODE)
    if paths.wireguard_private_key_file.exists():
        paths.wireguard_private_key_file.chmod(PRIVATE_FILE_MODE)
    if paths.openvpn_user_file.exists():
        paths.openvpn_user_file.chmod(PRIVATE_FILE_MODE)
    if paths.openvpn_password_file.exists():
        paths.openvpn_password_file.chmod(PRIVATE_FILE_MODE)
