#!/usr/bin/env sh
# Author: DrPlaga
set -eu

ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"

scripts/smoke-test.sh

if command -v shellcheck >/dev/null 2>&1; then
  shellcheck vpn-browser setup.sh install.sh uninstall.sh scripts/*.sh browser/entrypoint.sh
else
  echo "ShellCheck: SKIPPED - shellcheck not installed"
fi

if command -v hadolint >/dev/null 2>&1; then
  hadolint browser/Dockerfile
else
  echo "Hadolint: SKIPPED - hadolint not installed"
fi

if command -v trivy >/dev/null 2>&1; then
  trivy image --exit-code 1 --severity HIGH,CRITICAL vpn-browser-browser:local
else
  echo "Trivy: SKIPPED - trivy not installed"
fi

if command -v gitleaks >/dev/null 2>&1; then
  gitleaks detect --no-banner --redact
else
  echo "Gitleaks: SKIPPED - gitleaks not installed"
fi

scripts/integration-test.sh
scripts/killswitch-test.sh

echo "REAL VPN INTEGRATION TEST REQUIRED before release if integration-test was SKIPPED."
echo "PASS: release check completed with explicit skips where tools or Proton config were unavailable"
