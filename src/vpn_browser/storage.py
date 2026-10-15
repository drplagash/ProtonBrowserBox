# Copyright (c) 2026 DrPlaga. Licencia MIT (ver LICENSE).

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from vpn_browser.config import Settings
from vpn_browser.paths import ProjectPaths, ensure_private_dir


class StorageError(RuntimeError):
    pass


@dataclass(frozen=True)
class StorageUsage:
    path: Path
    used_bytes: int
    budget_bytes: int
    percent: float
    status: str
    detail: str


def directory_size_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    total = 0
    for item in path.rglob("*"):
        if item.is_file() and not item.is_symlink():
            total += item.stat().st_size
    return total


def profile_path(paths: ProjectPaths, settings: Settings) -> Path:
    if settings.persistent_browser_profile:
        return paths.browser_profile_dir
    return paths.ephemeral_browser_profile_dir


def profile_usage(paths: ProjectPaths, settings: Settings) -> StorageUsage:
    path = profile_path(paths, settings)
    budget_bytes = settings.disk_budget_mb * 1024 * 1024
    used_bytes = directory_size_bytes(path)
    percent = (used_bytes / budget_bytes) * 100 if budget_bytes else 100.0
    if used_bytes * 100 >= budget_bytes * 100:
        status = "FAIL"
        detail = "profile storage budget exceeded"
    elif used_bytes * 100 >= budget_bytes * 95:
        status = "WARNING"
        detail = "critical profile storage warning"
    elif used_bytes * 100 >= budget_bytes * 80:
        status = "WARNING"
        detail = "profile storage warning"
    else:
        status = "PASS"
        detail = "profile storage within budget"
    return StorageUsage(path, used_bytes, budget_bytes, percent, status, detail)


def prepare_browser_profile(paths: ProjectPaths, settings: Settings) -> Path:
    path = profile_path(paths, settings)
    if not settings.persistent_browser_profile and path.exists():
        shutil.rmtree(path)
    ensure_private_dir(path)
    usage = profile_usage(paths, settings)
    if usage.percent >= 100:
        raise StorageError(
            f"Browser profile storage budget exceeded: {usage.used_bytes} of "
            f"{usage.budget_bytes} bytes."
        )
    return path


def cleanup_ephemeral_profile(paths: ProjectPaths, settings: Settings) -> None:
    if not settings.persistent_browser_profile and paths.ephemeral_browser_profile_dir.exists():
        shutil.rmtree(paths.ephemeral_browser_profile_dir)
