#!/usr/bin/env python3
# Author: DrPlaga
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def compose_config() -> dict[str, Any]:
    completed = subprocess.run(
        ["docker", "compose", "config", "--format", "json"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if completed.returncode != 0:
        print(completed.stderr)
        fail("docker compose config failed")
    return json.loads(completed.stdout)


def main() -> int:
    config = compose_config()
    services = config.get("services", {})
    vpn = services.get("vpn", {})
    browser = services.get("browser", {})

    require(vpn.get("image") == "qmcgaw/gluetun:v3.41.3", "Gluetun image must be pinned")
    require("latest" not in vpn.get("image", ""), "Gluetun image must not use latest")
    require(vpn.get("privileged") in (None, False), "vpn must not be privileged")
    require(browser.get("privileged") in (None, False), "browser must not be privileged")
    for name, service in services.items():
        require(service.get("network_mode") != "host", f"{name} must not use host networking")
    require(vpn.get("cap_add") == ["NET_ADMIN"], "only vpn may add NET_ADMIN")
    require("cap_add" not in browser, "browser must not add capabilities")
    require(browser.get("cap_drop") == ["ALL"], "browser must drop all capabilities")
    require(browser.get("network_mode") == "service:vpn", "browser must share vpn network")
    require("networks" not in browser, "browser must not attach to a separate network")
    require("ports" not in browser, "browser must not publish ports")
    require("devices" not in browser, "browser must not mount host devices")
    require("secrets" not in browser, "browser must not receive VPN secrets")
    require(browser.get("read_only") is True, "browser root filesystem must be read-only")
    require(browser.get("pids_limit") == 512, "browser pids_limit must be set")
    require(
        "no-new-privileges:true" in browser.get("security_opt", []),
        "browser must set no-new-privileges",
    )

    env = vpn.get("environment", {})
    require(env.get("VPN_SERVICE_PROVIDER") == "protonvpn", "provider must be protonvpn")
    require(env.get("VPN_TYPE") == "wireguard", "VPN_TYPE must be wireguard")
    require(env.get("FREE_ONLY") == "on", "FREE_ONLY must be on")
    require(
        env.get("WIREGUARD_PRIVATE_KEY_SECRETFILE") == "/run/secrets/wireguard_private_key",
        "WireGuard private key must be read from Docker secret file",
    )
    require(env.get("FIREWALL_INPUT_PORTS") == "5800", "Gluetun firewall must allow web UI port")
    require(
        vpn.get("sysctls", {}).get("net.ipv6.conf.all.disable_ipv6") == "1",
        "IPv6 must be disabled until VPN IPv6 is proven safe",
    )
    require(
        vpn.get("sysctls", {}).get("net.ipv6.conf.default.disable_ipv6") == "1",
        "Default IPv6 must be disabled until VPN IPv6 is proven safe",
    )

    ports = vpn.get("ports", [])
    require(len(ports) == 1, "only vpn should publish exactly one port")
    port = ports[0]
    require(port.get("host_ip") == "127.0.0.1", "web UI must bind to 127.0.0.1")
    require(str(port.get("published")) == "5800", "web UI must publish configured default port")
    require(port.get("target") == 5800, "web UI target must be 5800")

    secrets = config.get("secrets", {})
    require("wireguard_private_key" in secrets, "wireguard secret must be declared")
    expected_secret = {
        "source": "wireguard_private_key",
        "target": "/run/secrets/wireguard_private_key",
    }
    require(
        vpn.get("secrets") == [expected_secret],
        "wireguard secret must be granted only to vpn",
    )

    dangerous_sources = {"/", "/home", "/var/run/docker.sock", "/run/docker.sock"}
    for service_name, service in services.items():
        for volume in service.get("volumes", []):
            source = volume.get("source")
            require(
                source not in dangerous_sources,
                f"{service_name} mounts dangerous source {source}",
            )

    print("PASS: compose structure")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
