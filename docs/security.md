# Security Model

Primary invariant:

```text
No VPN, no browser Internet.
```

This must be enforced by Docker network topology and Gluetun firewall behavior,
not by launcher checks alone.

## Current IPv6 Policy

IPv6 is disabled in the initial Compose topology. It should only be enabled
after real integration tests prove that browser IPv6 traffic exits exclusively
through the configured Proton tunnel and remains blocked when the VPN is down.

## Current DNS Policy

Firefox DNS-over-HTTPS is disabled by policy so DNS resolution follows the
resolver exposed inside the Gluetun namespace. This keeps DNS behavior tied to
the VPN namespace during the first implementation.

## Threat Model

| Threat | Impact | Mitigation | Residual risk | Verification |
| --- | --- | --- | --- | --- |
| VPN disconnected | Browser traffic could leak without structural isolation. | Browser uses `network_mode: service:vpn`; Gluetun firewall remains authoritative. | Docker or Gluetun bugs may still exist. | Real kill-switch test required. |
| Gluetun crash | Browser could lose network namespace connectivity. | No alternate browser network or host networking is configured. | Behavior must be verified per Docker version. | VPN container failure leak test required. |
| Tunnel handshake lost | Traffic could try to route outside tunnel. | Gluetun firewall/killswitch and no browser fallback route. | Needs live Proton validation. | Real VPN-down test required. |
| DNS failure | DNS could leak or fail open. | Firefox DoH disabled; DNS follows Gluetun namespace. | Resolver behavior depends on Gluetun. | DNS leak safety test required. |
| IPv6 leak | IPv6 could bypass IPv4-only protections. | IPv6 disabled in the namespace until proven safe. | Sites may observe no IPv6 support. | Compose sysctl validation PASS; live IPv6 test pending. |
| Browser compromise | Malicious page may attack browser/container. | Browser runs non-root, no Docker socket, dropped caps, read-only rootfs. | Container escape vulnerabilities remain possible. | Compose validation and image scans. |
| noVNC exposed to LAN | Anyone on LAN could use the browser. | Web UI published only on `127.0.0.1`. | Local malware on host could connect. | Compose port validation PASS. |
| Secret in `.env` | VPN secrets could be committed or exposed by `ps`. | Docker secret file paths; no private key or OpenVPN password in `.env` or CLI args. | Host compromise can read user files. | Secret tests and gitleaks. |
| Secret in logs | Private key could leak to console or CI. | Central redaction and no key printing. | Third-party tools may log unexpected data. | Unit tests and release checks. |
| Docker socket exposure | Browser compromise could control host Docker. | Docker socket is not mounted. | Host Docker daemon remains privileged. | Compose mount validation PASS. |
| Container escape | Attacker could reach host. | Reduced privileges, no privileged browser, no host network. | Docker/kernel vulnerabilities remain. | Security scans and dependency updates. |
| Host fingerprinting | Sites can still identify user. | Privacy prefs reduce telemetry, WebRTC and geolocation disabled. | Login, cookies, behavior, and fingerprinting remain. | Manual browser privacy review. |
| Browser profile permissions | Local users could read cookies/bookmarks. | Config/data dirs are private; profile is under XDG data. | Host admin or malware can read data. | Permission checks in doctor. |
| Stale server list | Free server locations may change. | Automatic mode always available; no fake hardcoded Free list. | Manual country selection is limited until stable dataset support exists. | Server command reports limitation. |
| Host compromise | Attacker can read traffic before/after browser, secrets, profile. | Out of scope for full prevention. | Complete compromise defeats local protections. | Documentation only. |

## Privacy Limits

This project does not provide anonymity guarantees. A website can still identify
the user through accounts, cookies, browser fingerprinting, behavior, payment
information, or host compromise. Proton VPN also does not make a user
untraceable.
