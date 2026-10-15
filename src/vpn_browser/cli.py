# Copyright (c) 2026 DrPlaga. Licencia MIT (ver LICENSE).

from __future__ import annotations

import argparse
import getpass
import ipaddress
import shutil
import sys
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

from vpn_browser.config import (
    ConfigError,
    Settings,
    describe_settings,
    load_settings,
    save_settings,
)
from vpn_browser.constants import DISPLAY_NAME, VERSION
from vpn_browser.docker import (
    DockerError,
    browser_memory_limit_bytes,
    run_compose,
    service_health,
    wait_for_service_health,
)
from vpn_browser.doctor import run_basic_checks
from vpn_browser.logging_utils import configure_logging, redact
from vpn_browser.paths import PRIVATE_FILE_MODE, ProjectPaths, ensure_base_directories, get_paths
from vpn_browser.secrets import (
    SecretError,
    fix_secret_permissions,
    write_openvpn_credentials,
    write_wireguard_private_key,
)
from vpn_browser.storage import (
    StorageError,
    cleanup_ephemeral_profile,
    prepare_browser_profile,
    profile_usage,
)
from vpn_browser.wireguard import WireGuardConfigError, parse_wireguard_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vpn-browser",
        description="Isolated browser appliance routed only through Proton VPN Free.",
    )
    parser.add_argument("--debug", action="store_true", help="show extra diagnostic output")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("start")
    subparsers.add_parser("stop")
    subparsers.add_parser("status")
    config_parser = subparsers.add_parser("config")
    config_parser.add_argument(
        "--openvpn-tcp",
        action="store_true",
        help="configure resources and Proton OpenVPN TCP/443 credentials",
    )
    server_parser = subparsers.add_parser("server")
    server_group = server_parser.add_mutually_exclusive_group()
    server_group.add_argument(
        "--auto",
        action="store_true",
        help="use Proton Free automatic server selection",
    )
    server_group.add_argument(
        "--country",
        metavar="COUNTRY",
        help="use Proton Free server selection limited to a country",
    )
    server_group.add_argument(
        "--exact",
        action="store_true",
        help="use the exact imported WireGuard peer when available",
    )
    server_group.add_argument(
        "--openvpn-tcp",
        action="store_true",
        help="use Proton OpenVPN over TCP/443",
    )
    logs_parser = subparsers.add_parser("logs")
    logs_parser.add_argument("--tail", default="200")
    subparsers.add_parser("doctor")
    subparsers.add_parser("clear-profile")
    subparsers.add_parser("reset")
    subparsers.add_parser("version")

    return parser


def _print_checks() -> int:
    failed = False
    for result in run_basic_checks(get_paths()):
        print(f"{result.status}: {result.name} - {redact(result.detail)}")
        failed = failed or result.status == "FAIL"
    return 1 if failed else 0


def _cmd_version() -> int:
    print(f"{DISPLAY_NAME} {VERSION}")
    return 0


def _cmd_status() -> int:
    paths = get_paths()
    print(DISPLAY_NAME)
    try:
        settings = load_settings(paths)
    except ConfigError as exc:
        print(f"Configuration: FAIL - {redact(exc)}")
        return 1
    if settings is None:
        print("Configuration: WARNING - not configured yet")
        print("VPN container: SKIPPED - no configuration")
        print("Browser: SKIPPED - no configuration")
        return 0
    print("Configuration: PASS")
    for line in describe_settings(settings):
        print(line)
    usage = profile_usage(paths, settings)
    print(
        f"Profile size: {usage.used_bytes} bytes "
        f"({usage.percent:.1f}% of {settings.disk_budget_mb} MB budget) - {usage.status}"
    )
    try:
        vpn_health = service_health(paths, settings, "vpn")
        browser_health = service_health(paths, settings, "browser")
        memory_limit = browser_memory_limit_bytes(paths, settings)
    except DockerError as exc:
        print(f"Docker: FAIL - {redact(exc)}")
        return 1
    expected_memory = settings.memory_limit_mb * 1024 * 1024
    memory_status = "PASS" if memory_limit == expected_memory else "FAIL"
    print(f"Runtime memory limit: {memory_status} - {memory_limit} bytes")
    print(f"VPN health: {vpn_health}")
    print(f"Browser health: {browser_health}")
    if settings.vpn_protocol == "openvpn":
        openvpn_ready = paths.openvpn_user_file.exists() and paths.openvpn_password_file.exists()
        print(f"OpenVPN credentials: {'PASS' if openvpn_ready else 'FAIL'}")
    else:
        wg_ready = paths.wireguard_private_key_file.exists()
        print(f"WireGuard secret: {'PASS' if wg_ready else 'FAIL'}")
    print("Kill switch: ACTIVE - enforced by Gluetun firewall and shared network namespace")
    return 0


def _ask_choice(prompt: str, choices: dict[str, str], default: str) -> str:
    print(prompt)
    for key, label in choices.items():
        print(f"{key}. {label}")
    answer = input(f"Select [{default}]: ").strip() or default
    while answer not in choices:
        answer = input(f"Select one of {', '.join(choices)} [{default}]: ").strip() or default
    return answer


def _ask_int(prompt: str, default: int, minimum: int, maximum: int) -> int:
    while True:
        raw = input(f"{prompt} [{default}]: ").strip()
        if not raw:
            return default
        try:
            value = int(raw)
        except ValueError:
            print("Enter a number.")
            continue
        if minimum <= value <= maximum:
            return value
        print(f"Enter a value between {minimum} and {maximum}.")


def _wireguard_conf_files(paths: ProjectPaths) -> list[str]:
    return sorted(
        str(path)
        for path in paths.wireguard_import_dir.glob("*.conf")
        if path.is_file()
    )


def _ask_wireguard_config_path(paths: ProjectPaths) -> str | None:
    conf_files = _wireguard_conf_files(paths)
    print(f"WireGuard config folder: {paths.wireguard_import_dir}")
    if len(conf_files) == 1:
        print(f"Using: {conf_files[0]}")
        return conf_files[0]
    if len(conf_files) > 1:
        choices = {str(index): path for index, path in enumerate(conf_files, start=1)}
        selected = _ask_choice("WireGuard configs found:", choices, "1")
        return choices[selected]

    answer = input("Path to Proton WireGuard .conf: ").strip()
    if answer:
        return answer
    print(f"ERROR: put one Proton WireGuard .conf file in {paths.wireguard_import_dir}.")
    return None


def _secure_wireguard_config_file(path: str) -> None:
    config_path = Path(path).expanduser()
    if config_path.exists() and config_path.is_file():
        config_path.chmod(PRIVATE_FILE_MODE)


def _cmd_config(openvpn_tcp: bool = False) -> int:
    paths = get_paths()
    ensure_base_directories(paths)
    print(f"{DISPLAY_NAME} - Initial Setup")
    if openvpn_tcp:
        print("This wizard configures Proton OpenVPN TCP/443 and browser resources.")
    else:
        print("This wizard imports a Proton WireGuard .conf from the project config folder.")

    profile_choice = _ask_choice(
        "Resource profile:",
        {
            "1": "LIGHT - 1024 MB RAM, 2048 MB profile budget",
            "2": "NORMAL - 2048 MB RAM, 4096 MB profile budget",
            "3": "COMFORT - 4096 MB RAM, 8192 MB profile budget",
            "4": "CUSTOM",
        },
        "2",
    )
    profile_map = {
        "1": ("light", 1024, 2048),
        "2": ("normal", 2048, 4096),
        "3": ("comfort", 4096, 8192),
    }
    if profile_choice == "4":
        memory_profile = "custom"
        memory_limit_mb = _ask_int("Browser RAM MB", 2048, 512, 65536)
        disk_budget_mb = _ask_int("Browser profile storage budget MB", 4096, 512, 1048576)
    else:
        memory_profile, memory_limit_mb, disk_budget_mb = profile_map[profile_choice]

    persistent_choice = _ask_choice(
        "Browser profile:",
        {"1": "Persistent", "2": "Ephemeral"},
        "1",
    )
    web_port = _ask_int("Local web port", 5800, 1024, 65535)
    resolution = input("Resolution [1920x1080]: ").strip() or "1920x1080"
    if openvpn_tcp:
        settings = Settings(
            memory_profile=memory_profile,
            memory_limit_mb=memory_limit_mb,
            disk_budget_mb=disk_budget_mb,
            persistent_browser_profile=persistent_choice == "1",
            web_port=web_port,
            resolution=resolution,
            vpn_protocol="openvpn",
        )
        return _configure_openvpn(paths, settings)
    wg_path = _ask_wireguard_config_path(paths)
    if wg_path is None:
        return 1
    _secure_wireguard_config_file(wg_path)

    try:
        parsed = parse_wireguard_config(wg_path)
    except WireGuardConfigError as exc:
        print(f"ERROR: {redact(exc)}", file=sys.stderr)
        return 1
    for warning in parsed.warnings:
        print(f"WARNING: {warning}")

    write_wireguard_private_key(paths, parsed.private_key)
    endpoint_is_ip = False
    if parsed.endpoint_ip:
        try:
            ipaddress.ip_address(parsed.endpoint_ip)
            endpoint_is_ip = True
        except ValueError:
            endpoint_is_ip = False
    provider_mode = (
        "custom"
        if (
            parsed.public_key
            and parsed.endpoint_ip
            and endpoint_is_ip
            and parsed.endpoint_port
            and parsed.addresses
        )
        else "proton"
    )
    settings = Settings(
        memory_profile=memory_profile,
        memory_limit_mb=memory_limit_mb,
        disk_budget_mb=disk_budget_mb,
        persistent_browser_profile=persistent_choice == "1",
        provider_mode=provider_mode,
        country_mode="automatic",
        country=None,
        web_port=web_port,
        resolution=resolution,
        wireguard_public_key=parsed.public_key,
        wireguard_endpoint_ip=parsed.endpoint_ip,
        wireguard_endpoint_port=parsed.endpoint_port,
        wireguard_addresses=list(parsed.addresses) if parsed.addresses else None,
        wireguard_persistent_keepalive=parsed.persistent_keepalive,
    )
    save_settings(paths, settings)
    fix_secret_permissions(paths)

    print("Configuration: PASS")
    print("WireGuard secret: PASS - stored with private permissions")
    if provider_mode == "custom":
        print("Server selection: Exact WireGuard config")
    else:
        print("Server selection: Automatic Free server")
    print("PrivateKey: [REDACTED]")
    return 0


def _cmd_start() -> int:
    paths = get_paths()
    try:
        settings = load_settings(paths)
    except ConfigError as exc:
        print(f"ERROR: {redact(exc)}", file=sys.stderr)
        return 1
    if settings is None:
        print(f"{DISPLAY_NAME} - Initial Setup")
        print("Configuration: WARNING - not configured yet")
        print("Run: vpn-browser config")
        print("Browser was NOT started.")
        print("No fallback network is enabled.")
        return 0
    if settings.vpn_protocol == "openvpn":
        if not paths.openvpn_user_file.exists() or not paths.openvpn_password_file.exists():
            print("ERROR: OpenVPN credentials not found.", file=sys.stderr)
            print("Run: vpn-browser server --openvpn-tcp", file=sys.stderr)
            print("Browser was NOT started.", file=sys.stderr)
            print("No fallback network is enabled.", file=sys.stderr)
            return 1
    elif not paths.wireguard_private_key_file.exists():
        print("ERROR: WireGuard secret not found.", file=sys.stderr)
        print("Run: vpn-browser config", file=sys.stderr)
        print("Browser was NOT started.", file=sys.stderr)
        print("No fallback network is enabled.", file=sys.stderr)
        return 1
    fix_secret_permissions(paths)
    try:
        usage = profile_usage(paths, settings)
        if usage.percent >= 100:
            raise StorageError(
                f"Browser profile storage budget exceeded: {usage.percent:.1f}% used."
            )
        if usage.status == "WARNING":
            print(
                f"WARNING: Browser profile storage is {usage.percent:.1f}% "
                f"of the configured budget."
            )
        prepare_browser_profile(paths, settings)
    except StorageError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        print("Browser was NOT started.", file=sys.stderr)
        print("No profile data was deleted automatically.", file=sys.stderr)
        return 1
    print(f"{DISPLAY_NAME}")
    print("Configuration: FOUND")
    if settings.vpn_protocol == "openvpn":
        print("VPN: Proton VPN / OpenVPN TCP")
        print(f"Port: {settings.openvpn_endpoint_port}")
    elif settings.provider_mode == "custom":
        print("VPN: WireGuard exact config")
        print("Provider: Proton config import")
    else:
        print("VPN: Proton VPN / WireGuard")
        print("Plan: Free")
    print("Kill switch: ACTIVE")
    print("Starting VPN...")
    try:
        run_compose(["up", "-d", "vpn"], paths, settings, timeout=180)
        if not wait_for_service_health(paths, settings, "vpn", timeout_seconds=90):
            print("VPN failed to become healthy after 90 seconds.", file=sys.stderr)
            print("Browser was NOT started.", file=sys.stderr)
            print("Network remains blocked.", file=sys.stderr)
            return 1
        print("VPN status: CONNECTED")
        print("Starting Firefox...")
        run_compose(["up", "-d", "browser"], paths, settings, timeout=180)
        if not wait_for_service_health(paths, settings, "browser", timeout_seconds=60):
            print("Browser failed to become healthy after 60 seconds.", file=sys.stderr)
            return 1
    except DockerError as exc:
        print(f"ERROR: {redact(exc)}", file=sys.stderr)
        print("Browser was NOT started or was left behind the VPN namespace.", file=sys.stderr)
        print("No fallback network is enabled.", file=sys.stderr)
        return 1
    print("Browser: READY")
    print()
    print("Open:")
    print(f"http://127.0.0.1:{settings.web_port}")
    return 0


def _load_required_settings() -> tuple[ProjectPaths, Settings] | None:
    paths = get_paths()
    try:
        settings = load_settings(paths)
    except ConfigError as exc:
        print(f"ERROR: {redact(exc)}", file=sys.stderr)
        return None
    if settings is None:
        print("Configuration: WARNING - not configured yet")
        print("Run: vpn-browser config")
        return None
    return paths, settings


def _cmd_stop() -> int:
    loaded = _load_required_settings()
    if loaded is None:
        return 0
    paths, settings = loaded
    try:
        run_compose(["down"], paths, settings, timeout=120)
        cleanup_ephemeral_profile(paths, settings)
    except DockerError as exc:
        print(f"ERROR: {redact(exc)}", file=sys.stderr)
        return 1
    print("Stopped.")
    return 0


def _cmd_logs(tail: str) -> int:
    loaded = _load_required_settings()
    if loaded is None:
        return 0
    paths, settings = loaded
    extra_secrets: list[str] = []
    try:
        extra_secrets = [
            path.read_text(encoding="utf-8").strip()
            for path in (
                paths.wireguard_private_key_file,
                paths.openvpn_user_file,
                paths.openvpn_password_file,
            )
            if path.exists()
        ]
        completed = run_compose(["logs", "--no-color", "--tail", tail], paths, settings, timeout=60)
    except (DockerError, OSError) as exc:
        print(f"ERROR: {redact(exc, extra_secrets=extra_secrets)}", file=sys.stderr)
        return 1
    print(redact(completed.stdout, extra_secrets=extra_secrets))
    return 0


def _has_exact_wireguard_metadata(settings: Settings) -> bool:
    return bool(
        settings.wireguard_public_key
        and settings.wireguard_endpoint_ip
        and settings.wireguard_endpoint_port
        and settings.wireguard_addresses
    )


def _server_summary(settings: Settings) -> str:
    if settings.vpn_protocol == "openvpn":
        return f"Proton OpenVPN TCP/{settings.openvpn_endpoint_port}"
    if settings.provider_mode == "custom":
        return "Exact imported WireGuard config"
    if settings.country_mode == "manual":
        return f"Proton Free / {settings.country}"
    return "Proton Free / automatic"


def _save_server_settings(
    paths: ProjectPaths,
    settings: Settings,
    next_settings: Settings,
) -> None:
    save_settings(paths, next_settings)
    print(f"Server selection: {_server_summary(next_settings)}")
    if (
        settings.vpn_protocol != next_settings.vpn_protocol
        or settings.provider_mode != next_settings.provider_mode
        or settings.openvpn_protocol != next_settings.openvpn_protocol
        or settings.openvpn_endpoint_port != next_settings.openvpn_endpoint_port
    ) or (
        settings.country_mode != next_settings.country_mode
        or settings.country != next_settings.country
    ):
        print("Restart the appliance for the change to take effect.")


def _settings_for_country(settings: Settings, country: str) -> Settings:
    return replace(
        settings,
        vpn_protocol="wireguard",
        provider_mode="proton",
        country_mode="manual",
        country=country.strip(),
    )


def _configure_openvpn(paths: ProjectPaths, settings: Settings) -> int:
    print("Proton OpenVPN TCP/443")
    print("Credentials: https://account.protonvpn.com/account -> OpenVPN username")
    print("Use the OpenVPN/IKEv2 credentials, not your Proton login password.")
    username = input("OpenVPN/IKEv2 username: ").strip()
    password = getpass.getpass("OpenVPN/IKEv2 password: ").strip()
    try:
        write_openvpn_credentials(paths, username, password)
        next_settings = replace(
            settings,
            vpn_protocol="openvpn",
            provider_mode="proton",
            country_mode="automatic",
            country=None,
            openvpn_protocol="tcp",
            openvpn_endpoint_port=443,
        )
        _save_server_settings(paths, settings, next_settings)
    except (ConfigError, SecretError) as exc:
        print(f"ERROR: {redact(exc)}", file=sys.stderr)
        return 1
    print("Configuration: PASS")
    print("OpenVPN credentials: PASS - stored with private permissions")
    return 0


def _cmd_server(
    auto: bool = False,
    country: str | None = None,
    exact: bool = False,
    openvpn_tcp: bool = False,
) -> int:
    paths = get_paths()
    try:
        settings = load_settings(paths)
    except ConfigError as exc:
        print(f"ERROR: {redact(exc)}", file=sys.stderr)
        return 1
    if settings is None:
        if not openvpn_tcp:
            print("Configuration: WARNING - not configured yet")
            print("Run: vpn-browser config")
            return 0
        settings = Settings.default()
        ensure_base_directories(paths)
        print("Configuration: default settings will be created for OpenVPN TCP/443")

    if auto:
        next_settings = replace(
            settings,
            vpn_protocol="wireguard",
            provider_mode="proton",
            country_mode="automatic",
            country=None,
        )
        _save_server_settings(paths, settings, next_settings)
        return 0

    if country is not None:
        try:
            _save_server_settings(paths, settings, _settings_for_country(settings, country))
        except ConfigError as exc:
            print(f"ERROR: {redact(exc)}", file=sys.stderr)
            return 1
        return 0

    if exact:
        if not _has_exact_wireguard_metadata(settings):
            print("ERROR: no exact WireGuard peer metadata is available.", file=sys.stderr)
            print("Run: vpn-browser config", file=sys.stderr)
            return 1
        next_settings = replace(settings, vpn_protocol="wireguard", provider_mode="custom")
        try:
            _save_server_settings(paths, settings, next_settings)
        except ConfigError as exc:
            print(f"ERROR: {redact(exc)}", file=sys.stderr)
            return 1
        return 0

    if openvpn_tcp:
        return _configure_openvpn(paths, settings)

    print("VPN Exit")
    print(f"Current: {_server_summary(settings)}")
    choices = {
        "1": "Proton WireGuard automatic / fastest available Free server",
        "2": "Proton WireGuard manual Free country",
        "3": "Proton OpenVPN TCP/443",
    }
    if _has_exact_wireguard_metadata(settings):
        choices["4"] = "Exact imported WireGuard config"
    choice = _ask_choice("Server selection:", choices, "1")

    if choice == "1":
        next_settings = replace(
            settings,
            vpn_protocol="wireguard",
            provider_mode="proton",
            country_mode="automatic",
            country=None,
        )
    elif choice == "2":
        while True:
            country_answer = input("Country: ").strip()
            try:
                next_settings = _settings_for_country(settings, country_answer)
                _save_server_settings(paths, settings, next_settings)
            except ConfigError as exc:
                print(f"ERROR: {redact(exc)}")
                continue
            return 0
    elif choice == "3":
        return _cmd_server(openvpn_tcp=True)
    else:
        next_settings = replace(settings, vpn_protocol="wireguard", provider_mode="custom")

    try:
        _save_server_settings(paths, settings, next_settings)
    except ConfigError as exc:
        print(f"ERROR: {redact(exc)}", file=sys.stderr)
        return 1
    return 0


def _cmd_clear_profile() -> int:
    paths = get_paths()
    confirmation = input("Type DELETE PROFILE to remove the browser profile: ").strip()
    if confirmation != "DELETE PROFILE":
        print("Profile not removed.")
        return 0
    if paths.browser_profile_dir.exists():
        shutil.rmtree(paths.browser_profile_dir)
    print("Browser profile removed.")
    return 0


def _cmd_reset() -> int:
    paths = get_paths()
    confirmation = input("Type DELETE CONFIG to remove settings and VPN secret: ").strip()
    if confirmation != "DELETE CONFIG":
        print("Configuration not removed.")
        return 0
    for path in (
        paths.settings_file,
        paths.compose_override_file,
        paths.wireguard_private_key_file,
        paths.openvpn_user_file,
        paths.openvpn_password_file,
    ):
        if path.exists():
            path.unlink()
    print("Configuration and VPN secret removed.")
    print("Browser profile was not removed. Use vpn-browser clear-profile for that.")
    return 0


def _not_implemented(command: str) -> int:
    print(f"{command}: SKIPPED - implemented in a later phase")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(debug=args.debug)
    command = args.command or "start"

    if command == "version":
        return _cmd_version()
    if command == "doctor":
        return _print_checks()
    if command == "status":
        return _cmd_status()
    if command == "start":
        return _cmd_start()
    if command == "config":
        return _cmd_config(openvpn_tcp=args.openvpn_tcp)
    if command == "stop":
        return _cmd_stop()
    if command == "logs":
        return _cmd_logs(args.tail)
    if command == "server":
        return _cmd_server(
            auto=args.auto,
            country=args.country,
            exact=args.exact,
            openvpn_tcp=args.openvpn_tcp,
        )
    if command == "clear-profile":
        return _cmd_clear_profile()
    if command == "reset":
        return _cmd_reset()

    parser.print_help()
    return 0
