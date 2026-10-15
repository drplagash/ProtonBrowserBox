# Copyright (c) 2026 DrPlaga. Licencia MIT (ver LICENSE).

from __future__ import annotations

import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from vpn_browser.config import ConfigError, load_settings
from vpn_browser.docker import REPO_ROOT, browser_memory_limit_bytes
from vpn_browser.paths import ProjectPaths
from vpn_browser.secrets import check_secret_permissions
from vpn_browser.storage import profile_usage


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    detail: str


def _run(command: list[str]) -> tuple[int, str]:
    try:
        completed = subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)
    return completed.returncode, completed.stdout.strip()


def run_basic_checks(paths: ProjectPaths) -> list[CheckResult]:
    results: list[CheckResult] = []

    system = platform.system()
    machine = platform.machine()
    if system == "Linux" and machine in {"x86_64", "aarch64", "arm64"}:
        results.append(CheckResult("OS/architecture", "PASS", f"{system} {machine}"))
    else:
        results.append(CheckResult("OS/architecture", "WARNING", f"{system} {machine}"))

    docker_path = shutil.which("docker")
    if docker_path:
        code, output = _run(["docker", "version", "--format", "{{.Server.Version}}"])
        status = "PASS" if code == 0 else "FAIL"
        detail = output or docker_path
        results.append(CheckResult("Docker daemon", status, detail))
    else:
        results.append(CheckResult("Docker daemon", "FAIL", "docker command not found"))

    if docker_path:
        code, output = _run(["docker", "compose", "version", "--short"])
        status = "PASS" if code == 0 else "FAIL"
        results.append(CheckResult("Docker Compose v2", status, output or "not available"))

    tun = Path("/dev/net/tun")
    if system == "Linux":
        results.append(
            CheckResult(
                "TUN device",
                "PASS" if tun.exists() else "FAIL",
                str(tun) if tun.exists() else "/dev/net/tun missing",
            )
        )
    else:
        results.append(CheckResult("TUN device", "SKIPPED", "Linux-only check"))

    try:
        settings = load_settings(paths)
    except ConfigError as exc:
        results.append(CheckResult("Configuration", "FAIL", str(exc)))
        settings = None
    else:
        if settings is None:
            results.append(CheckResult("Configuration", "WARNING", "not configured yet"))
        else:
            results.append(CheckResult("Configuration", "PASS", str(paths.settings_file)))

    if settings is not None and settings.vpn_protocol == "openvpn":
        if paths.openvpn_user_file.exists() and paths.openvpn_password_file.exists():
            results.append(CheckResult("OpenVPN credentials", "PASS", "secret files exist"))
        else:
            results.append(
                CheckResult(
                    "OpenVPN credentials",
                    "WARNING",
                    "run vpn-browser server --openvpn-tcp",
                )
            )
    elif paths.wireguard_private_key_file.exists():
        results.append(CheckResult("WireGuard secret", "PASS", "secret file exists"))
    else:
        results.append(CheckResult("WireGuard secret", "WARNING", "not configured yet"))

    for check in check_secret_permissions(paths):
        detail = check.detail if check.actual_mode is None else f"{check.detail}: {check.path}"
        results.append(CheckResult(f"Permissions: {check.path.name}", check.status, detail))

    code, output = _run(["python3", str(REPO_ROOT / "scripts" / "validate-compose.py")])
    results.append(
        CheckResult(
            "Compose security structure",
            "PASS" if code == 0 else "FAIL",
            output or "compose validation did not produce output",
        )
    )

    if settings is None:
        results.append(CheckResult("Disk budget", "SKIPPED", "not configured yet"))
        results.append(CheckResult("Runtime memory limit", "SKIPPED", "not configured yet"))
    else:
        usage = profile_usage(paths, settings)
        results.append(
            CheckResult(
                "Disk budget",
                usage.status,
                f"{usage.used_bytes} bytes used; {usage.percent:.1f}% of budget",
            )
        )
        try:
            actual_memory = browser_memory_limit_bytes(paths, settings)
        except Exception as exc:
            results.append(CheckResult("Runtime memory limit", "FAIL", str(exc)))
        else:
            expected_memory = settings.memory_limit_mb * 1024 * 1024
            results.append(
                CheckResult(
                    "Runtime memory limit",
                    "PASS" if actual_memory == expected_memory else "FAIL",
                    f"{actual_memory} bytes configured; expected {expected_memory}",
                )
            )

    return results
