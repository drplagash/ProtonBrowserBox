# Author: DrPlaga

import stat
from pathlib import Path

from vpn_browser.logging_utils import redact
from vpn_browser.paths import get_paths
from vpn_browser.secrets import (
    check_secret_permissions,
    fix_secret_permissions,
    write_openvpn_credentials,
    write_wireguard_private_key,
)

VALID_KEY = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="


def test_write_secret_uses_private_permissions(tmp_path: Path) -> None:
    paths = get_paths({"HOME": str(tmp_path)})
    write_wireguard_private_key(paths, VALID_KEY)
    assert paths.wireguard_private_key_file.read_text(encoding="utf-8").strip() == VALID_KEY
    assert stat.S_IMODE(paths.config_dir.stat().st_mode) == 0o700
    assert stat.S_IMODE(paths.secrets_dir.stat().st_mode) == 0o700
    assert stat.S_IMODE(paths.wireguard_private_key_file.stat().st_mode) == 0o600


def test_check_secret_permissions_warns_and_fix_corrects(tmp_path: Path) -> None:
    paths = get_paths({"HOME": str(tmp_path)})
    write_wireguard_private_key(paths, VALID_KEY)
    paths.secrets_dir.chmod(0o755)
    paths.wireguard_private_key_file.chmod(0o644)
    assert any(result.status == "WARNING" for result in check_secret_permissions(paths))
    fix_secret_permissions(paths)
    assert all(result.status == "PASS" for result in check_secret_permissions(paths))


def test_write_openvpn_credentials_uses_private_permissions(tmp_path: Path) -> None:
    paths = get_paths({"HOME": str(tmp_path)})
    write_openvpn_credentials(paths, "user", "password")
    assert paths.openvpn_user_file.read_text(encoding="utf-8").strip() == "user"
    assert paths.openvpn_password_file.read_text(encoding="utf-8").strip() == "password"
    assert stat.S_IMODE(paths.openvpn_user_file.stat().st_mode) == 0o600
    assert stat.S_IMODE(paths.openvpn_password_file.stat().st_mode) == 0o600


def test_redaction_hides_fixture_secret() -> None:
    assert VALID_KEY not in redact(f"PrivateKey = {VALID_KEY}", [VALID_KEY])
