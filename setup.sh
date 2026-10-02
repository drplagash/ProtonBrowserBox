#!/usr/bin/env sh
# Author: DrPlaga
set -eu

PROJECT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
VPN_BROWSER_CONFIG_DIR=${VPN_BROWSER_CONFIG_DIR:-"$PROJECT_DIR/config/vpn"}
export VPN_BROWSER_CONFIG_DIR

mode=""
case "${1:-}" in
  "") ;;
  --openvpn-tcp) mode=openvpn ;;
  --wireguard) mode=wireguard ;;
  --help|-h)
    printf '%s\n' "ProtonBrowserBox - Author: DrPlaga" \
      "Usage: sh setup.sh [--openvpn-tcp | --wireguard]" \
      "Without options, reuse existing settings or ask for a VPN mode." \
      "Requires Python 3.11+, Docker Engine, Compose v2 and /dev/net/tun."
    exit 0
    ;;
  *)
    printf '%s\n' "ERROR: unknown option. Run: sh setup.sh --help" >&2
    exit 2
    ;;
esac
if [ "$#" -gt 1 ]; then
  printf '%s\n' "ERROR: choose only one VPN mode." >&2
  exit 2
fi

sh "$PROJECT_DIR/install.sh"

if [ -z "$mode" ] && [ -f "$VPN_BROWSER_CONFIG_DIR/settings.json" ]; then
  printf '%s\n' "Using existing configuration."
  exec "$PROJECT_DIR/vpn-browser"
fi

if [ -f "$VPN_BROWSER_CONFIG_DIR/settings.json" ]; then
  "$PROJECT_DIR/vpn-browser" stop
fi

if [ -z "$mode" ]; then
  printf '%s\n' "VPN mode:" "1. OpenVPN TCP/443" "2. WireGuard .conf import"
  while :; do
    printf '%s' "Select [1]: "
    read -r choice
    case "$choice" in
      ""|1) mode=openvpn; break ;;
      2) mode=wireguard; break ;;
      *) printf '%s\n' "Select 1 or 2." ;;
    esac
  done
fi

case "$mode" in
  openvpn) "$PROJECT_DIR/vpn-browser" config --openvpn-tcp ;;
  wireguard)
    printf 'Drop your Proton .conf in: %s/wireguard/\n' "$VPN_BROWSER_CONFIG_DIR"
    printf '%s' "Press Enter when the file is ready: "
    read -r _
    "$PROJECT_DIR/vpn-browser" config
    ;;
esac

exec "$PROJECT_DIR/vpn-browser"
