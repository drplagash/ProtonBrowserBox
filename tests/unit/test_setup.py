# Copyright (c) 2026 DrPlaga. Licencia MIT (ver LICENSE).

import os
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def setup_project(tmp_path):
    project = tmp_path / "project with spaces"
    project.mkdir()
    shutil.copy2(Path(__file__).parents[2] / "setup.sh", project / "setup.sh")
    (project / "install.sh").write_text(
        '#!/bin/sh\n# Author: DrPlaga\n'
        'printf "install\\n" >> "$PBB_TEST_LOG"\n'
        'exit "${PBB_TEST_INSTALL_EXIT:-0}"\n',
        encoding="utf-8",
    )
    launcher = project / "vpn-browser"
    launcher.write_text(
        '#!/bin/sh\n# Author: DrPlaga\n'
        'printf "launcher:%s\\n" "$*" >> "$PBB_TEST_LOG"\n'
        'if [ "${1:-}" = config ]; then exit "${PBB_TEST_CONFIG_EXIT:-0}"; fi\n',
        encoding="utf-8",
    )
    launcher.chmod(0o755)
    log = tmp_path / "commands.log"
    env = dict(os.environ, VPN_BROWSER_CONFIG_DIR=str(tmp_path / "config"), PBB_TEST_LOG=str(log))
    return project, log, env


@pytest.mark.parametrize(
    ("arguments", "answers", "configuration"),
    [
        ([], "\n", "config --openvpn-tcp"),
        ([], "2\n\n", "config"),
        (["--openvpn-tcp"], "", "config --openvpn-tcp"),
        (["--wireguard"], "\n", "config"),
    ],
)
def test_setup_configures_then_starts(setup_project, arguments, answers, configuration):
    project, log, env = setup_project
    result = subprocess.run(
        ["sh", str(project / "setup.sh"), *arguments],
        input=answers, text=True, capture_output=True, env=env, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert log.read_text().splitlines() == ["install", f"launcher:{configuration}", "launcher:"]


def test_setup_reuses_configuration_without_requesting_credentials(setup_project):
    project, log, env = setup_project
    config_dir = Path(env["VPN_BROWSER_CONFIG_DIR"])
    config_dir.mkdir()
    (config_dir / "settings.json").write_text("{}", encoding="utf-8")
    result = subprocess.run(
        ["sh", str(project / "setup.sh")],
        input="", text=True, capture_output=True, env=env, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert log.read_text().splitlines() == ["install", "launcher:"]


@pytest.mark.parametrize("failure", ["PBB_TEST_INSTALL_EXIT", "PBB_TEST_CONFIG_EXIT"])
def test_setup_never_starts_after_failed_install_or_configuration(setup_project, failure):
    project, log, env = setup_project
    env[failure] = "1"
    result = subprocess.run(
        ["sh", str(project / "setup.sh"), "--openvpn-tcp"],
        input="", text=True, capture_output=True, env=env, check=False,
    )
    assert result.returncode == 1
    assert "launcher:" not in log.read_text().splitlines()
