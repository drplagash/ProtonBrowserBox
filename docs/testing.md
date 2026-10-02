# Testing

## Local Smoke Test

```sh
scripts/smoke-test.sh
```

This runs Python lint when available, unit/integration tests that do not require
Proton credentials, Compose validation, and the browser image build.

## Proton Integration Test

This test requires a real Proton VPN WireGuard configuration file. It imports
only the WireGuard private key into an isolated temporary XDG home and starts
the appliance.

```sh
VPN_BROWSER_PROTON_CONF=/path/to/proton.conf scripts/integration-test.sh
```

If no config is provided, the test reports:

```text
Proton Integration: SKIPPED - no user WireGuard configuration provided.
```

## Kill Switch Test

Active kill-switch testing is still pending. The project must not be released
as fully validated until a real WireGuard-down and VPN-container-failure leak
test passes.

Current status:

```sh
scripts/killswitch-test.sh
```

returns `SKIPPED`.

## Release Check

```sh
scripts/release-check.sh
```

The release check runs all local checks available without Proton credentials and
reports missing optional tools as `SKIPPED`, not `PASS`.
