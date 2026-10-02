# Author: DrPlaga

from pathlib import Path

import pytest

from vpn_browser.wireguard import WireGuardConfigError, parse_wireguard_config

VALID_KEY = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="


def write_conf(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_valid_wireguard_conf(tmp_path: Path) -> None:
    conf = write_conf(
        tmp_path / "proton.conf",
        "[Interface]\n"
        f"PrivateKey = {VALID_KEY}\n"
        "Address = 10.2.0.2/32, 2a07:b944::2:2/128\n"
        "[Peer]\n"
        "PublicKey = AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=\n"
        "Endpoint = 95.173.217.71:51820\n"
        "PersistentKeepalive = 25\n",
    )
    parsed = parse_wireguard_config(conf)
    assert parsed.private_key == VALID_KEY
    assert parsed.addresses == ("10.2.0.2/32",)
    assert parsed.public_key == "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    assert parsed.endpoint_ip == "95.173.217.71"
    assert parsed.endpoint_port == 51820
    assert parsed.persistent_keepalive == 25


def test_valid_wireguard_conf_with_crlf_and_spaces(tmp_path: Path) -> None:
    conf = write_conf(
        tmp_path / "proton.conf",
        f"[Interface]\r\nPrivateKey =   {VALID_KEY}   \r\n",
    )
    assert parse_wireguard_config(conf).private_key == VALID_KEY


def test_missing_interface_fails(tmp_path: Path) -> None:
    conf = write_conf(tmp_path / "bad.conf", f"[Peer]\nPrivateKey = {VALID_KEY}\n")
    with pytest.raises(WireGuardConfigError, match="missing \\[Interface\\]"):
        parse_wireguard_config(conf)


def test_missing_private_key_fails(tmp_path: Path) -> None:
    conf = write_conf(tmp_path / "bad.conf", "[Interface]\nAddress = 10.2.0.2/32\n")
    with pytest.raises(WireGuardConfigError, match="missing Interface PrivateKey"):
        parse_wireguard_config(conf)


def test_malformed_private_key_fails(tmp_path: Path) -> None:
    conf = write_conf(tmp_path / "bad.conf", "[Interface]\nPrivateKey = not-base64!!\n")
    with pytest.raises(WireGuardConfigError, match="Base64"):
        parse_wireguard_config(conf)


def test_invalid_private_key_length_fails(tmp_path: Path) -> None:
    conf = write_conf(tmp_path / "bad.conf", "[Interface]\nPrivateKey = AAAA\n")
    with pytest.raises(WireGuardConfigError, match="32 bytes"):
        parse_wireguard_config(conf)


def test_duplicate_private_key_fails(tmp_path: Path) -> None:
    conf = write_conf(
        tmp_path / "bad.conf",
        f"[Interface]\nPrivateKey = {VALID_KEY}\nPrivateKey = {VALID_KEY}\n",
    )
    with pytest.raises(WireGuardConfigError, match="Duplicate WireGuard option"):
        parse_wireguard_config(conf)


def test_missing_file_fails(tmp_path: Path) -> None:
    with pytest.raises(WireGuardConfigError, match="does not exist"):
        parse_wireguard_config(tmp_path / "missing.conf")


def test_permissive_file_returns_warning(tmp_path: Path) -> None:
    conf = write_conf(tmp_path / "proton.conf", f"[Interface]\nPrivateKey = {VALID_KEY}\n")
    conf.chmod(0o644)
    parsed = parse_wireguard_config(conf)
    assert parsed.warnings
