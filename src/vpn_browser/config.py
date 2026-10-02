# Author: DrPlaga

from __future__ import annotations

import ipaddress
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from vpn_browser.constants import (
    DEFAULT_WEB_PORT,
    RESOURCE_PROFILES,
    SUPPORTED_SCHEMA_VERSION,
)
from vpn_browser.paths import PRIVATE_FILE_MODE, ProjectPaths, ensure_base_directories


class ConfigError(RuntimeError):
    pass


COUNTRY_RE = re.compile(r"^[A-Za-z][A-Za-z .'-]{1,80}$")


@dataclass(frozen=True)
class Settings:
    schema_version: int = SUPPORTED_SCHEMA_VERSION
    memory_profile: str = "normal"
    memory_limit_mb: int = 2048
    disk_budget_mb: int = 4096
    persistent_browser_profile: bool = True
    vpn_protocol: str = "wireguard"
    provider_mode: str = "proton"
    country_mode: str = "automatic"
    country: str | None = None
    web_port: int = DEFAULT_WEB_PORT
    resolution: str = "1920x1080"
    browser: str = "firefox-esr"
    wireguard_public_key: str | None = None
    wireguard_endpoint_ip: str | None = None
    wireguard_endpoint_port: int | None = None
    wireguard_addresses: list[str] | None = None
    wireguard_persistent_keepalive: int | None = None
    wireguard_implementation: str | None = None
    wireguard_mtu: int | None = None
    openvpn_protocol: str = "tcp"
    openvpn_endpoint_port: int = 443

    @classmethod
    def default(cls) -> Settings:
        profile = RESOURCE_PROFILES["normal"]
        return cls(
            memory_profile="normal",
            memory_limit_mb=profile["memory_limit_mb"],
            disk_budget_mb=profile["disk_budget_mb"],
        )


def validate_settings(settings: Settings) -> None:
    if settings.schema_version != SUPPORTED_SCHEMA_VERSION:
        raise ConfigError(
            f"Unsupported settings schema_version {settings.schema_version}; "
            f"expected {SUPPORTED_SCHEMA_VERSION}."
        )
    if settings.memory_profile not in {*RESOURCE_PROFILES, "custom"}:
        raise ConfigError(f"Invalid memory_profile: {settings.memory_profile}")
    if settings.memory_limit_mb < 512:
        raise ConfigError("memory_limit_mb must be at least 512.")
    if settings.disk_budget_mb < 512:
        raise ConfigError("disk_budget_mb must be at least 512.")
    if not 1024 <= settings.web_port <= 65535:
        raise ConfigError("web_port must be between 1024 and 65535.")
    if settings.vpn_protocol not in {"wireguard", "openvpn"}:
        raise ConfigError("vpn_protocol must be wireguard or openvpn.")
    if settings.provider_mode not in {"proton", "custom"}:
        raise ConfigError("provider_mode must be proton or custom.")
    if settings.vpn_protocol == "openvpn" and settings.provider_mode == "custom":
        raise ConfigError("OpenVPN mode only supports Proton provider mode.")
    if settings.country_mode not in {"automatic", "manual"}:
        raise ConfigError("country_mode must be automatic or manual.")
    if settings.country_mode == "automatic" and settings.country is not None:
        raise ConfigError("country must be null when country_mode is automatic.")
    if settings.country_mode == "manual":
        if settings.country is None:
            raise ConfigError("country is required when country_mode is manual.")
        if not COUNTRY_RE.fullmatch(settings.country):
            raise ConfigError("country contains unsupported characters.")
    if (
        settings.wireguard_endpoint_port is not None
        and not 1 <= settings.wireguard_endpoint_port <= 65535
    ):
        raise ConfigError("wireguard_endpoint_port must be between 1 and 65535.")
    if settings.wireguard_addresses is not None:
        if not settings.wireguard_addresses:
            raise ConfigError("wireguard_addresses cannot be empty when set.")
        if not all(
            isinstance(address, str) and "/" in address for address in settings.wireguard_addresses
        ):
            raise ConfigError("wireguard_addresses must contain CIDR strings.")
    if settings.wireguard_implementation not in {None, "auto", "kernelspace", "userspace"}:
        raise ConfigError("wireguard_implementation must be auto, kernelspace, or userspace.")
    if settings.wireguard_mtu is not None and not 576 <= settings.wireguard_mtu <= 1500:
        raise ConfigError("wireguard_mtu must be between 576 and 1500.")
    if settings.openvpn_protocol not in {"tcp", "udp"}:
        raise ConfigError("openvpn_protocol must be tcp or udp.")
    if not 1 <= settings.openvpn_endpoint_port <= 65535:
        raise ConfigError("openvpn_endpoint_port must be between 1 and 65535.")
    if settings.provider_mode == "custom":
        required = {
            "wireguard_public_key": settings.wireguard_public_key,
            "wireguard_endpoint_ip": settings.wireguard_endpoint_ip,
            "wireguard_endpoint_port": settings.wireguard_endpoint_port,
            "wireguard_addresses": settings.wireguard_addresses,
        }
        missing = [
            name
            for name, value in required.items()
            if value is None or value == "" or value == []
        ]
        if missing:
            raise ConfigError(
                "custom provider mode requires: " + ", ".join(sorted(set(missing)))
            )
        try:
            ipaddress.ip_address(settings.wireguard_endpoint_ip or "")
        except ValueError as exc:
            raise ConfigError("custom provider mode requires a WireGuard endpoint IP.") from exc


def settings_from_dict(data: dict[str, Any]) -> Settings:
    allowed = set(Settings.__dataclass_fields__)
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise ConfigError(f"Unknown settings keys: {', '.join(unknown)}")
    try:
        settings = Settings(**data)
    except TypeError as exc:
        raise ConfigError(str(exc)) from exc
    validate_settings(settings)
    return settings


def load_settings(paths: ProjectPaths) -> Settings | None:
    if not paths.settings_file.exists():
        return None
    try:
        data = json.loads(paths.settings_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Settings file is not valid JSON: {paths.settings_file}") from exc
    if not isinstance(data, dict):
        raise ConfigError("Settings file must contain a JSON object.")
    return settings_from_dict(data)


def save_settings(paths: ProjectPaths, settings: Settings) -> None:
    validate_settings(settings)
    ensure_base_directories(paths)
    tmp_file = paths.settings_file.with_suffix(".json.tmp")
    tmp_file.write_text(json.dumps(asdict(settings), indent=2) + "\n", encoding="utf-8")
    tmp_file.chmod(PRIVATE_FILE_MODE)
    tmp_file.replace(paths.settings_file)


def describe_settings(settings: Settings) -> list[str]:
    country = settings.country if settings.country_mode == "manual" else "Automatic"
    profile = "Persistent" if settings.persistent_browser_profile else "Ephemeral"
    if settings.vpn_protocol == "openvpn":
        provider = (
            f"Proton OpenVPN "
            f"{settings.openvpn_protocol.upper()}/{settings.openvpn_endpoint_port}"
        )
    else:
        provider = "Exact WireGuard config" if settings.provider_mode == "custom" else "Proton Free"
    return [
        f"RAM: {settings.memory_limit_mb} MB",
        f"Storage budget: {settings.disk_budget_mb} MB",
        f"Provider mode: {provider}",
        f"Country: {country}",
        f"Profile: {profile}",
        f"Browser: {settings.browser}",
        f"Web port: {settings.web_port}",
    ]


def config_exists(path: Path) -> bool:
    return path.exists()
