# Architecture

The intended runtime architecture is a two-service Docker Compose application:

- `vpn`: Gluetun, Proton VPN Free, WireGuard or OpenVPN TCP/443, DNS,
  firewall, kill switch.
- `browser`: Firefox ESR exposed through noVNC, sharing the VPN namespace with
  `network_mode: "service:vpn"`.

The browser service must not attach to a separate Docker network.

The VPN service publishes the browser UI from the shared namespace and binds it
only to `127.0.0.1`. The browser service itself publishes no ports.

IPv6 is disabled in the initial Compose topology until a real Proton/Gluetun
IPv6-through-VPN test proves that IPv6 exits exclusively through the tunnel.

The structural validation script checks these invariants against Docker
Compose's normalized configuration:

- `browser.network_mode == service:vpn`
- the browser service has no `networks`, `ports`, host devices, or VPN secrets
- no service uses `network_mode: host`
- only the VPN service publishes a port, and only on `127.0.0.1`
- the browser service runs with dropped capabilities, read-only rootfs, and
  `no-new-privileges`
- IPv6 is disabled until explicitly validated through the VPN
