# Author: DrPlaga

from pathlib import Path

import pytest

from vpn_browser.config import Settings
from vpn_browser.paths import get_paths
from vpn_browser.storage import (
    StorageError,
    cleanup_ephemeral_profile,
    directory_size_bytes,
    prepare_browser_profile,
    profile_path,
    profile_usage,
)


def write_bytes(path: Path, size: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)


def test_directory_size_counts_files(tmp_path: Path) -> None:
    write_bytes(tmp_path / "a.bin", 5)
    write_bytes(tmp_path / "nested" / "b.bin", 7)
    assert directory_size_bytes(tmp_path) == 12


@pytest.mark.parametrize(
    ("used", "expected"),
    [
        (79, "PASS"),
        (80, "WARNING"),
        (95, "WARNING"),
        (100, "FAIL"),
    ],
)
def test_profile_budget_thresholds(tmp_path: Path, used: int, expected: str) -> None:
    paths = get_paths({"HOME": str(tmp_path)})
    settings = Settings.default().__class__(disk_budget_mb=1)
    target_bytes = (used * 1024 * 1024 + 99) // 100
    write_bytes(paths.browser_profile_dir / "blob", target_bytes)
    assert profile_usage(paths, settings).status == expected


def test_prepare_ephemeral_profile_clears_previous_data(tmp_path: Path) -> None:
    paths = get_paths({"HOME": str(tmp_path)})
    settings = Settings.default().__class__(persistent_browser_profile=False)
    stale = paths.ephemeral_browser_profile_dir / "stale"
    write_bytes(stale, 10)
    path = prepare_browser_profile(paths, settings)
    assert path == paths.ephemeral_browser_profile_dir
    assert not stale.exists()
    assert profile_path(paths, settings) == paths.ephemeral_browser_profile_dir


def test_cleanup_ephemeral_profile_removes_only_ephemeral(tmp_path: Path) -> None:
    paths = get_paths({"HOME": str(tmp_path)})
    settings = Settings.default().__class__(persistent_browser_profile=False)
    write_bytes(paths.ephemeral_browser_profile_dir / "temp", 10)
    write_bytes(paths.browser_profile_dir / "keep", 10)
    cleanup_ephemeral_profile(paths, settings)
    assert not paths.ephemeral_browser_profile_dir.exists()
    assert (paths.browser_profile_dir / "keep").exists()


def test_prepare_profile_blocks_over_budget(tmp_path: Path) -> None:
    paths = get_paths({"HOME": str(tmp_path)})
    settings = Settings.default().__class__(disk_budget_mb=1)
    write_bytes(paths.browser_profile_dir / "blob", 1024 * 1024)
    with pytest.raises(StorageError):
        prepare_browser_profile(paths, settings)
