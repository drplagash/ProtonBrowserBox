# Troubleshooting

## Docker daemon unavailable

Run:

```sh
docker version
docker compose version
```

The current user must be able to talk to Docker. Do not run the browser service
with host networking or privileged mode to work around Docker permission issues.

## `/dev/net/tun` missing

On Linux, Gluetun/WireGuard requires `/dev/net/tun`. The project reports this as
a host problem and does not make kernel changes automatically.

## WireGuard secret missing

Run:

```sh
./vpn-browser config
```

Do not place the private key in `.env`, `compose.yaml`, shell history, logs, or
GitHub Actions.

## Browser does not start

Check:

```sh
./vpn-browser status
./vpn-browser logs
scripts/network-diagnose.sh
```

The browser is started only after the VPN service is healthy. If the VPN fails,
the browser is not given a direct fallback path.

## Profile storage warning

The disk budget is a browser profile budget, not a Docker quota. Docker images
and layers use extra disk outside this budget.

Use:

```sh
./vpn-browser clear-profile
```

only after confirming you want to remove browser profile data.
