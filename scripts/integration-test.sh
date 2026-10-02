#!/usr/bin/env sh
# Author: DrPlaga
set -eu

ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
CONF=${VPN_BROWSER_PROTON_CONF:-${1:-}}
ORIGINAL_DOCKER_CONFIG=${DOCKER_CONFIG:-"$HOME/.docker"}
CONFIG_OUTPUT=${TMPDIR:-/tmp}/vpn-browser-config.out
TEST_COUNTRY=${VPN_BROWSER_TEST_COUNTRY:-}
WG_IMPLEMENTATION=${VPN_BROWSER_WG_IMPLEMENTATION:-}
PROVIDER_MODE=${VPN_BROWSER_PROVIDER_MODE:-}
WG_MTU=${VPN_BROWSER_WG_MTU:-}

if [ -z "$CONF" ]; then
  echo "Proton Integration: SKIPPED - no user WireGuard configuration provided."
  echo "Set VPN_BROWSER_PROTON_CONF=/path/to/proton.conf to run this test."
  exit 0
fi

if [ ! -f "$CONF" ]; then
  echo "Proton Integration: FAIL - WireGuard configuration not found: $CONF" >&2
  exit 1
fi

tmp_home=$(mktemp -d)
test_config_dir=$tmp_home/config/vpn
test_data_dir=$tmp_home/config/vpn/data
test_import_dir=$test_config_dir/wireguard
test_settings=$test_config_dir/settings.json
cleanup() {
  DOCKER_CONFIG="$ORIGINAL_DOCKER_CONFIG" HOME="$tmp_home" XDG_CONFIG_HOME='' XDG_DATA_HOME='' \
    VPN_BROWSER_CONFIG_DIR=$test_config_dir VPN_BROWSER_DATA_DIR=$test_data_dir \
    "$ROOT/vpn-browser" stop >/dev/null 2>&1 || true
  rm -f "$CONFIG_OUTPUT"
  python3 - "$tmp_home" <<'PY'
from pathlib import Path
import shutil
import sys

path = Path(sys.argv[1])
if path.exists() and path.name.startswith("tmp."):
    shutil.rmtree(path)
PY
}
trap cleanup EXIT INT TERM

export HOME="$tmp_home"
export DOCKER_CONFIG="$ORIGINAL_DOCKER_CONFIG"
export VPN_BROWSER_CONFIG_DIR="$test_config_dir"
export VPN_BROWSER_DATA_DIR="$test_data_dir"
unset XDG_CONFIG_HOME
unset XDG_DATA_HOME
mkdir -p "$test_import_dir"
cp "$CONF" "$test_import_dir/proton.conf"

printf '2\n1\n5800\n1920x1080\n' | "$ROOT/vpn-browser" config >"$CONFIG_OUTPUT"

if [ -n "$TEST_COUNTRY" ]; then
  python3 - "$test_settings" "$TEST_COUNTRY" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
country = sys.argv[2]
data = json.loads(path.read_text(encoding="utf-8"))
data["country_mode"] = "manual"
data["country"] = country
path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY
fi

if [ -n "$WG_IMPLEMENTATION" ]; then
  python3 - "$test_settings" "$WG_IMPLEMENTATION" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
implementation = sys.argv[2]
data = json.loads(path.read_text(encoding="utf-8"))
data["wireguard_implementation"] = implementation
path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY
fi

if [ -n "$PROVIDER_MODE" ]; then
  python3 - "$test_settings" "$PROVIDER_MODE" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
provider_mode = sys.argv[2]
data = json.loads(path.read_text(encoding="utf-8"))
data["provider_mode"] = provider_mode
path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY
fi

if [ -n "$WG_MTU" ]; then
  python3 - "$test_settings" "$WG_MTU" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
mtu = int(sys.argv[2])
data = json.loads(path.read_text(encoding="utf-8"))
data["wireguard_mtu"] = mtu
path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY
fi

if grep -F "PrivateKey =" "$CONFIG_OUTPUT" >/dev/null; then
  echo "Secret leak test: FAIL - PrivateKey appeared in config output" >&2
  exit 1
fi

if ! "$ROOT/vpn-browser" start; then
  echo "Proton Integration: FAIL - VPN did not become healthy."
  "$ROOT/vpn-browser" logs --tail 120 || true
  exit 1
fi

"$ROOT/vpn-browser" status

python3 - <<'PY'
import urllib.request

with urllib.request.urlopen("http://127.0.0.1:5800/", timeout=10) as response:
    if response.status != 200:
        raise SystemExit(f"Browser HTTP check: FAIL - status {response.status}")
print("Browser HTTP check: PASS")
PY

echo "Proton Integration: PASS"
echo "Kill switch validation: SKIPPED - run scripts/killswitch-test.sh once implemented for active leak tests."
