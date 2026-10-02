#!/usr/bin/env bash
# Author: DrPlaga
set -Eeuo pipefail

display_number="${DISPLAY#:}"
screen="${RESOLUTION}x24"
profile_dir="${FIREFOX_PROFILE:-/home/browser/.mozilla/firefox/default}"

mkdir -p "$profile_dir" /tmp/.X11-unix "$XDG_CACHE_HOME"

pids=()

cleanup() {
  for pid in "${pids[@]:-}"; do
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done
}
trap cleanup EXIT INT TERM

Xvfb "$DISPLAY" -screen 0 "$screen" -nolisten tcp &
pids+=("$!")

openbox >/tmp/openbox.log 2>&1 &
pids+=("$!")

x11vnc \
  -display "$DISPLAY" \
  -forever \
  -shared \
  -rfbport "$VNC_PORT" \
  -listen 127.0.0.1 \
  -nopw \
  -xkb \
  -quiet >/tmp/x11vnc.log 2>&1 &
pids+=("$!")

websockify \
  --web=/usr/share/novnc \
  "0.0.0.0:${WEB_PORT}" \
  "127.0.0.1:${VNC_PORT}" >/tmp/websockify.log 2>&1 &
pids+=("$!")

firefox-esr \
  --no-remote \
  --new-instance \
  --profile "$profile_dir" \
  about:blank &
firefox_pid="$!"
pids+=("$firefox_pid")

printf 'Browser display :%s ready on 127.0.0.1:%s\n' "$display_number" "$WEB_PORT"
wait "$firefox_pid"
