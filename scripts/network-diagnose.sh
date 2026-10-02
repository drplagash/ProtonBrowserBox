#!/usr/bin/env sh
# Author: DrPlaga
set -eu

ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON=${PYTHON:-python3}
TIMEOUT=${VPN_BROWSER_DIAG_TIMEOUT:-45}

export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
export VPN_BROWSER_CONFIG_DIR="${VPN_BROWSER_CONFIG_DIR:-$ROOT/config/vpn}"
export VPN_BROWSER_DATA_DIR="${VPN_BROWSER_DATA_DIR:-$ROOT/config/vpn/data}"

say() {
  printf '%s\n' "$*"
}

section() {
  printf '\n== %s ==\n' "$*"
}

section "Host internet"
if command -v curl >/dev/null 2>&1; then
  if curl -4 --connect-timeout 8 -fsS https://cloudflare.com/cdn-cgi/trace \
    | sed -n '1,6p'; then
    say "Host HTTPS: PASS"
  else
    say "Host HTTPS: FAIL - host cannot reach Cloudflare over HTTPS"
  fi
else
  say "Host HTTPS: SKIPPED - curl not found"
fi

section "Host requirements"
"$ROOT/vpn-browser" doctor

section "Current VPN settings"
"$PYTHON" - <<'PY'
from vpn_browser.config import load_settings
from vpn_browser.paths import get_paths

settings = load_settings(get_paths())
if settings is None:
    raise SystemExit("Configuration: FAIL - run ./vpn-browser config first")

print(f"Provider mode: {settings.provider_mode}")
print(f"Country mode: {settings.country_mode}")
if settings.wireguard_endpoint_ip:
    print(f"Imported endpoint: {settings.wireguard_endpoint_ip}:{settings.wireguard_endpoint_port}")
print(f"WireGuard implementation: {settings.wireguard_implementation or 'default'}")
print(f"WireGuard MTU: {settings.wireguard_mtu or 'default'}")
PY

section "UDP route smoke test"
"$PYTHON" - <<'PY'
import socket
from vpn_browser.config import load_settings
from vpn_browser.paths import get_paths

settings = load_settings(get_paths())
target = settings.wireguard_endpoint_ip if settings and settings.wireguard_endpoint_ip else "1.1.1.1"
port = settings.wireguard_endpoint_port if settings and settings.wireguard_endpoint_port else 51820

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(2)
try:
    sock.connect((target, int(port)))
    local = sock.getsockname()
    sock.send(b"vpn-browser-diagnostic")
except OSError as exc:
    print(f"UDP local route: FAIL - {exc}")
else:
    print(f"UDP local route: PASS - local {local[0]}:{local[1]} -> {target}:{port}")
    print("UDP remote acceptance: UNKNOWN - WireGuard/UDP usually does not reply to probes")
finally:
    sock.close()
PY

section "Gluetun VPN health probe"
say "Starting only the vpn service for up to ${TIMEOUT}s..."
set +e
"$PYTHON" - "$TIMEOUT" <<'PY'
import sys
import time

from vpn_browser.config import load_settings
from vpn_browser.docker import DockerError, run_compose, service_health
from vpn_browser.paths import get_paths

timeout = int(sys.argv[1])
paths = get_paths()
settings = load_settings(paths)
if settings is None:
    raise SystemExit("Configuration: FAIL - run ./vpn-browser config first")

try:
    run_compose(["up", "-d", "vpn"], paths, settings, timeout=180)
except DockerError as exc:
    raise SystemExit(f"VPN start: FAIL - {exc}")

deadline = time.monotonic() + timeout
last = None
while time.monotonic() < deadline:
    health = service_health(paths, settings, "vpn")
    if health != last:
        print(f"VPN health: {health}")
        last = health
    if health == "healthy":
        print("VPN health probe: PASS")
        raise SystemExit(0)
    time.sleep(2)

print("VPN health probe: FAIL - VPN did not become healthy before timeout")
raise SystemExit(1)
PY
probe_status=$?
set -e

section "Recent VPN logs"
"$ROOT/vpn-browser" logs --tail 120 || true

section "Cleanup"
"$ROOT/vpn-browser" stop || true

section "Result"
if [ "$probe_status" -eq 0 ]; then
  say "Network appears compatible with this VPN configuration."
  say "Run: ./vpn-browser"
  exit 0
fi

say "Network is not currently passing the VPN health check."
say "If logs show repeated 'Wireguard setup is complete' followed by TLS/DNS timeouts,"
say "the usual causes are UDP/51820 blocked, NAT/virtualization dropping UDP, or a bad Proton config."
exit 1
