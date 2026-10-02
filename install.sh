#!/usr/bin/env sh
# Author: DrPlaga
set -eu

PROJECT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
PYTHON=${PYTHON:-python3}
PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONPATH
OS=$(uname -s)
ARCH=$(uname -m)
HOME_DIR=${HOME:?HOME is required}
VPN_BROWSER_CONFIG_DIR=${VPN_BROWSER_CONFIG_DIR:-"$PROJECT_DIR/config/vpn"}
VPN_BROWSER_DATA_DIR=${VPN_BROWSER_DATA_DIR:-"$PROJECT_DIR/config/vpn/data"}
BIN_DIR="$HOME_DIR/.local/bin"
LINK="$BIN_DIR/vpn-browser"
export VPN_BROWSER_CONFIG_DIR
export VPN_BROWSER_DATA_DIR

printf '%s\n' "VPN Browser installer"

case "$OS" in
  Linux) ;;
  *)
    printf '%s\n' "WARNING: $OS is experimental. Linux is the supported target for v1."
    ;;
esac

case "$ARCH" in
  x86_64|aarch64|arm64) ;;
  *)
    printf '%s\n' "WARNING: unsupported architecture for v1: $ARCH"
    ;;
esac

command -v "$PYTHON" >/dev/null 2>&1 || {
  printf '%s\n' "ERROR: python3 not found" >&2
  exit 1
}

"$PYTHON" -c 'import sys; sys.exit(sys.version_info < (3, 11))' || {
  printf '%s\n' "ERROR: Python 3.11 or newer is required" >&2
  exit 1
}

command -v docker >/dev/null 2>&1 || {
  printf '%s\n' "ERROR: docker not found" >&2
  exit 1
}

docker version >/dev/null 2>&1 || {
  printf '%s\n' "ERROR: Docker daemon is not reachable by this user" >&2
  exit 1
}

docker compose version >/dev/null 2>&1 || {
  printf '%s\n' "ERROR: Docker Compose v2 is not available" >&2
  exit 1
}

if [ "$OS" = "Linux" ] && [ ! -c /dev/net/tun ]; then
  printf '%s\n' "ERROR: /dev/net/tun is missing. WireGuard cannot run without TUN." >&2
  exit 1
fi

mkdir -p "$VPN_BROWSER_CONFIG_DIR/secrets" "$VPN_BROWSER_CONFIG_DIR/wireguard" \
  "$VPN_BROWSER_DATA_DIR" "$BIN_DIR"
chmod 700 "$VPN_BROWSER_CONFIG_DIR" "$VPN_BROWSER_CONFIG_DIR/secrets" \
  "$VPN_BROWSER_CONFIG_DIR/wireguard" "$VPN_BROWSER_DATA_DIR"

if [ -e "$LINK" ] && [ ! -L "$LINK" ]; then
  printf '%s\n' "ERROR: $LINK exists and is not a symlink. Not overwriting it." >&2
  exit 1
fi

ln -sfn "$PROJECT_DIR/vpn-browser" "$LINK"

"$PYTHON" -m vpn_browser doctor
printf '%s\n' "Launcher installed: $LINK"
printf '%s\n' "Project config: $VPN_BROWSER_CONFIG_DIR"
printf '%s\n' "Drop Proton WireGuard .conf files in: $VPN_BROWSER_CONFIG_DIR/wireguard"
printf '%s\n' "Run: vpn-browser config"
printf '%s\n' "No VPN was started and no Proton password was requested."
