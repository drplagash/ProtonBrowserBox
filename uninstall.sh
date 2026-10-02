#!/usr/bin/env sh
# Author: DrPlaga
set -eu

PROJECT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
HOME_DIR=${HOME:?HOME is required}
VPN_BROWSER_CONFIG_DIR=${VPN_BROWSER_CONFIG_DIR:-"$PROJECT_DIR/config/vpn"}
VPN_BROWSER_DATA_DIR=${VPN_BROWSER_DATA_DIR:-"$PROJECT_DIR/config/vpn/data"}
LINK="$HOME_DIR/.local/bin/vpn-browser"

printf '%s\n' "VPN Browser uninstall"

if [ -L "$LINK" ] && [ "$(readlink "$LINK")" = "$PROJECT_DIR/vpn-browser" ]; then
  rm "$LINK"
  printf '%s\n' "Removed launcher symlink: $LINK"
else
  printf '%s\n' "Launcher symlink not found for this checkout: $LINK"
fi

printf '%s' "Remove configuration and secrets in $VPN_BROWSER_CONFIG_DIR? [y/N] "
read -r remove_config
case "$remove_config" in
  y|Y|yes|YES)
    rm -rf "$VPN_BROWSER_CONFIG_DIR"
    printf '%s\n' "Removed configuration and secrets."
    ;;
  *)
    printf '%s\n' "Kept configuration and secrets."
    ;;
esac

printf '%s' "Remove browser profile data in $VPN_BROWSER_DATA_DIR? [y/N] "
read -r remove_data
case "$remove_data" in
  y|Y|yes|YES)
    rm -rf "$VPN_BROWSER_DATA_DIR"
    printf '%s\n' "Removed browser profile data."
    ;;
  *)
    printf '%s\n' "Kept browser profile data."
    ;;
esac
