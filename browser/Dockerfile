# Author: DrPlaga

FROM debian:13-slim

ENV DEBIAN_FRONTEND=noninteractive

# Rebuild with current Debian security updates instead of freezing package versions.
# hadolint ignore=DL3008,DL3005
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        dbus-x11 \
        firefox-esr \
        fonts-dejavu-core \
        novnc \
        openbox \
        procps \
        tini \
        websockify \
        x11vnc \
        xvfb \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 1000 browser \
    && useradd --uid 1000 --gid 1000 --create-home --shell /usr/sbin/nologin browser \
    && mkdir -p /home/browser/.mozilla/firefox/default \
    && ln -sf /usr/share/novnc/vnc.html /usr/share/novnc/index.html \
    && chown -R browser:browser /home/browser

COPY policies.json /usr/lib/firefox-esr/distribution/policies.json
COPY entrypoint.sh /usr/local/bin/vpn-browser-entrypoint

RUN chmod 0644 /usr/lib/firefox-esr/distribution/policies.json \
    && chmod 0755 /usr/local/bin/vpn-browser-entrypoint

USER browser
ENV HOME=/home/browser \
    DISPLAY=:0 \
    RESOLUTION=1920x1080 \
    WEB_PORT=5800 \
    VNC_PORT=5900 \
    FIREFOX_PROFILE=/home/browser/.mozilla/firefox/default \
    XDG_CACHE_HOME=/tmp/browser-cache \
    NO_AT_BRIDGE=1

EXPOSE 5800

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/vpn-browser-entrypoint"]
