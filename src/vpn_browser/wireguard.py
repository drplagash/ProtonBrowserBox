# Copyright (c) 2026 DrPlaga. Licencia MIT (ver LICENSE).

from __future__ import annotations

import base64
import binascii
import configparser
import ipaddress
import stat
from dataclasses import dataclass
from pathlib import Path


class WireGuardConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class WireGuardConfig:
    private_key: str
    public_key: str | None = None
    endpoint_ip: str | None = None
    endpoint_port: int | None = None
    addresses: tuple[str, ...] = ()
    persistent_keepalive: int | None = None
    warnings: tuple[str, ...] = ()


def _decode_wireguard_key(value: str) -> bytes:
    try:
        decoded = base64.b64decode(value, validate=True)
    except binascii.Error as exc:
        raise WireGuardConfigError("PrivateKey is not valid Base64.") from exc
    if len(decoded) != 32:
        raise WireGuardConfigError("PrivateKey must decode to exactly 32 bytes.")
    return decoded


def _permission_warnings(path: Path) -> list[str]:
    mode = stat.S_IMODE(path.stat().st_mode)
    warnings = []
    if mode & 0o077:
        warnings.append(
            "WireGuard config file is readable by group or others. "
            "The imported secret will be stored with 0600 permissions."
        )
    return warnings


def _csv_values(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


def _parse_endpoint(value: str) -> tuple[str, int]:
    host, separator, port = value.strip().rpartition(":")
    if not separator or not host or not port:
        raise WireGuardConfigError("Peer Endpoint must be in host:port format.")
    try:
        parsed_port = int(port)
    except ValueError as exc:
        raise WireGuardConfigError("Peer Endpoint port must be numeric.") from exc
    if not 1 <= parsed_port <= 65535:
        raise WireGuardConfigError("Peer Endpoint port must be between 1 and 65535.")
    return host.strip("[]"), parsed_port


def _ipv4_addresses(addresses: tuple[str, ...]) -> tuple[str, ...]:
    ipv4 = []
    for address in addresses:
        try:
            interface = ipaddress.ip_interface(address)
        except ValueError as exc:
            raise WireGuardConfigError(f"Invalid Interface Address: {address}") from exc
        if interface.version == 4:
            ipv4.append(address)
    return tuple(ipv4)


def parse_wireguard_config(path: Path | str) -> WireGuardConfig:
    config_path = Path(path).expanduser()
    if not config_path.exists():
        raise WireGuardConfigError(f"WireGuard config file does not exist: {config_path}")
    if not config_path.is_file():
        raise WireGuardConfigError(f"WireGuard config path is not a file: {config_path}")

    parser = configparser.ConfigParser(
        interpolation=None,
        strict=True,
        delimiters=("=",),
        inline_comment_prefixes=("#", ";"),
    )
    parser.optionxform = str
    try:
        with config_path.open("r", encoding="utf-8", newline=None) as handle:
            parser.read_file(handle)
    except configparser.DuplicateOptionError as exc:
        raise WireGuardConfigError(f"Duplicate WireGuard option: {exc.option}") from exc
    except configparser.DuplicateSectionError as exc:
        raise WireGuardConfigError(f"Duplicate WireGuard section: {exc.section}") from exc
    except configparser.Error as exc:
        raise WireGuardConfigError(f"Invalid WireGuard config syntax: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise WireGuardConfigError("WireGuard config must be UTF-8 text.") from exc

    if not parser.has_section("Interface"):
        raise WireGuardConfigError("WireGuard config is missing [Interface].")
    if not parser.has_option("Interface", "PrivateKey"):
        raise WireGuardConfigError("WireGuard config is missing Interface PrivateKey.")

    private_key = parser.get("Interface", "PrivateKey").strip()
    if not private_key:
        raise WireGuardConfigError("Interface PrivateKey is empty.")
    _decode_wireguard_key(private_key)

    addresses: tuple[str, ...] = ()
    if parser.has_option("Interface", "Address"):
        addresses = _ipv4_addresses(_csv_values(parser.get("Interface", "Address")))

    public_key = None
    endpoint_ip = None
    endpoint_port = None
    persistent_keepalive = None
    if parser.has_section("Peer"):
        if parser.has_option("Peer", "PublicKey"):
            public_key = parser.get("Peer", "PublicKey").strip()
        if parser.has_option("Peer", "Endpoint"):
            endpoint_ip, endpoint_port = _parse_endpoint(parser.get("Peer", "Endpoint"))
        if parser.has_option("Peer", "PersistentKeepalive"):
            try:
                persistent_keepalive = int(parser.get("Peer", "PersistentKeepalive").strip())
            except ValueError as exc:
                raise WireGuardConfigError("Peer PersistentKeepalive must be numeric.") from exc

    return WireGuardConfig(
        private_key=private_key,
        public_key=public_key,
        endpoint_ip=endpoint_ip,
        endpoint_port=endpoint_port,
        addresses=addresses,
        persistent_keepalive=persistent_keepalive,
        warnings=tuple(_permission_warnings(config_path)),
    )
