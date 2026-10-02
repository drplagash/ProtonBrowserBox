# Contributing

Thanks for helping improve ProtonBrowserBox, maintained by DrPlaga.

Keep `# Author: DrPlaga` in project source files and scripts, after the shebang
when present. Keep the package author metadata and license attribution aligned.
Never commit local VPN configurations, credentials, logs, or browser profiles.
Runtime files belong in the ignored `config/vpn/` directory.

Security-sensitive changes should keep the central invariant intact:

```text
Browser -> Gluetun / Proton VPN (WireGuard or OpenVPN) -> Internet
```

Do not introduce host networking, privileged browser containers, Docker socket
mounts, secrets in environment files, or fallback networking.
