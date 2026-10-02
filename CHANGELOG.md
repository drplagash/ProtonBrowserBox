# Changelog

## 0.1.0 - Unreleased

- Name the public project ProtonBrowserBox and attribute project code to DrPlaga.
- Add a single guided `setup.sh` entry point for installation, configuration, and start.
- Document Proton credentials, all CLI commands, and troubleshooting in Spanish.
- Add resource configuration for OpenVPN TCP/443 without a WireGuard import.
- Remove OpenVPN secrets on confirmed reset and redact their values in CLI logs.
- Exclude VPN configuration and key files from Git and Docker build contexts.
- Refresh Debian base packages and Firefox security updates during image builds.

- Start project skeleton.
- Add Python launcher foundation.
- Add XDG path handling and basic settings model.
- Add redacting logging utilities.
- Add unit tests for phase 2 behavior.
- Add initial configuration wizard, WireGuard config parser, and private secret storage.
- Add initial Gluetun Compose topology and structural validation.
- Add first hardened Firefox ESR/noVNC browser image.
- Add profile storage budgeting, ephemeral profile handling, and runtime memory validation.
- Add smoke, integration, kill-switch placeholder, and release-check scripts.
- Add CI workflow and expanded security/install/testing documentation.
- Add idempotent installer and conservative uninstaller.
- Add usable server selection command for automatic, country-limited, and exact
  imported WireGuard modes.
- Store launcher runtime configuration in project-local `config/vpn/`.
- Auto-import Proton WireGuard `.conf` files from `config/vpn/wireguard/`.
- Add a network diagnostic script for host, UDP route, and Gluetun health checks.
- Add Proton OpenVPN TCP/443 mode with local secret storage for OpenVPN credentials.
