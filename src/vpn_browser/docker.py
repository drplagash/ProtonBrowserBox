# Author: DrPlaga

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from vpn_browser.config import Settings
from vpn_browser.paths import ProjectPaths
from vpn_browser.storage import profile_path


class DockerError(RuntimeError):
    pass


REPO_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_FILE = REPO_ROOT / "compose.yaml"


def prepare_compose_override(paths: ProjectPaths, settings: Settings) -> Path | None:
    environment: dict[str, object] = {}
    secrets: dict[str, Path] = {}
    service_secrets: list[str] = []
    if settings.vpn_protocol == "openvpn":
        environment["VPN_TYPE"] = "openvpn"
        environment["OPENVPN_PROTOCOL"] = settings.openvpn_protocol
        environment["OPENVPN_ENDPOINT_PORT"] = settings.openvpn_endpoint_port
        environment["OPENVPN_USER_SECRETFILE"] = "/run/secrets/openvpn_user"
        environment["OPENVPN_PASSWORD_SECRETFILE"] = "/run/secrets/openvpn_password"
        secrets["openvpn_user"] = paths.openvpn_user_file
        secrets["openvpn_password"] = paths.openvpn_password_file
        service_secrets.extend(["openvpn_user", "openvpn_password"])
    elif settings.provider_mode == "custom":
        environment["FREE_ONLY"] = None
        environment["VPN_SERVICE_PROVIDER"] = "custom"
        environment["WIREGUARD_ENDPOINT_IP"] = settings.wireguard_endpoint_ip
        environment["WIREGUARD_ENDPOINT_PORT"] = settings.wireguard_endpoint_port
        environment["WIREGUARD_PUBLIC_KEY"] = settings.wireguard_public_key
        environment["WIREGUARD_ADDRESSES"] = ",".join(settings.wireguard_addresses or [])
        environment["WIREGUARD_ALLOWED_IPS"] = "0.0.0.0/0"
        if settings.wireguard_persistent_keepalive:
            environment["WIREGUARD_PERSISTENT_KEEPALIVE_INTERVAL"] = (
                f"{settings.wireguard_persistent_keepalive}s"
            )
    elif settings.country_mode == "manual":
        environment["SERVER_COUNTRIES"] = settings.country
    if settings.wireguard_implementation:
        environment["WIREGUARD_IMPLEMENTATION"] = settings.wireguard_implementation
    if settings.wireguard_mtu:
        environment["WIREGUARD_MTU"] = settings.wireguard_mtu

    if not environment and not secrets:
        if paths.compose_override_file.exists():
            paths.compose_override_file.unlink()
        return None

    paths.config_dir.mkdir(parents=True, exist_ok=True)
    lines = ["services:", "  vpn:", "    environment:"]
    for key, value in sorted(environment.items()):
        lines.append(f"      {key}: {json.dumps(value)}")
    if service_secrets:
        lines.append("    secrets:")
        for name in service_secrets:
            lines.append(f"      - {name}")
    if secrets:
        lines.append("secrets:")
        for name, path in sorted(secrets.items()):
            lines.append(f"  {name}:")
            lines.append(f"    file: {json.dumps(str(path))}")
    paths.compose_override_file.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    return paths.compose_override_file


def compose_env(paths: ProjectPaths, settings: Settings) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "VPN_BROWSER_WIREGUARD_PRIVATE_KEY_FILE": str(paths.wireguard_private_key_file),
            "VPN_BROWSER_PROFILE_DIR": str(profile_path(paths, settings)),
            "VPN_BROWSER_WEB_PORT": str(settings.web_port),
            "VPN_BROWSER_BROWSER_MEMORY_MB": str(settings.memory_limit_mb),
            "VPN_BROWSER_VPN_MEMORY_MB": "256",
        }
    )
    return env


def run_compose(
    args: list[str],
    paths: ProjectPaths,
    settings: Settings,
    timeout: int = 120,
) -> subprocess.CompletedProcess[str]:
    command = ["docker", "compose", "-f", str(COMPOSE_FILE)]
    override = prepare_compose_override(paths, settings)
    if override is not None:
        command.extend(["-f", str(override)])
    command.extend(args)
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=compose_env(paths, settings),
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if completed.returncode != 0:
        output = completed.stderr.strip() or completed.stdout.strip()
        raise DockerError(output or f"docker compose failed: {' '.join(args)}")
    return completed


def compose_config_json(paths: ProjectPaths, settings: Settings) -> dict[str, Any]:
    completed = run_compose(["config", "--format", "json"], paths, settings, timeout=45)
    return json.loads(completed.stdout)


def browser_memory_limit_bytes(paths: ProjectPaths, settings: Settings) -> int:
    config = compose_config_json(paths, settings)
    value = config["services"]["browser"]["mem_limit"]
    return int(value)


def compose_service_container_id(
    paths: ProjectPaths,
    settings: Settings,
    service: str,
) -> str | None:
    completed = run_compose(["ps", "-q", service], paths, settings, timeout=30)
    container_id = completed.stdout.strip()
    return container_id or None


def inspect_container(container_id: str, template: str) -> str:
    completed = subprocess.run(
        ["docker", "inspect", container_id, "--format", template],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if completed.returncode != 0:
        raise DockerError(completed.stderr.strip() or completed.stdout.strip())
    return completed.stdout.strip()


def service_health(paths: ProjectPaths, settings: Settings, service: str) -> str:
    container_id = compose_service_container_id(paths, settings, service)
    if container_id is None:
        return "not-running"
    try:
        health = inspect_container(
            container_id,
            "{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}",
        )
    except DockerError:
        return "unknown"
    return health or "unknown"


def wait_for_service_health(
    paths: ProjectPaths,
    settings: Settings,
    service: str,
    timeout_seconds: int,
) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if service_health(paths, settings, service) == "healthy":
            return True
        time.sleep(2)
    return False
