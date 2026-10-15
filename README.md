# ProtonBrowserBox

![ProtonBrowserBox](docs/cover.jpg)

Firefox ESR in a container, accessible from your local browser and connected to
Proton VPN through Gluetun. Compatible with **OpenVPN TCP/443** and **WireGuard**.
The browser shares the VPN container's network and starts once the VPN passes
its health check.

## The problem

Running a whole-machine VPN is overkill when you only want one browsing session to go through it, and a VPN app can drop silently and leak your real IP while the browser keeps working. Setting up a browser that is guaranteed to use the VPN, and to stop when it fails, means wiring containers, a kill switch, credentials and profiles by hand.

ProtonBrowserBox does that wiring for you: a Firefox in a container that shares the network of a Gluetun/Proton VPN container, so it only runs while the VPN is healthy and its traffic cannot bypass the tunnel. One script sets it up, and the rest of your machine keeps its normal connection.

## How it works

```text
Your local browser -> 127.0.0.1:5800 -> Firefox in the container
                                           |
                                    Gluetun / Proton VPN -> Internet
```

The VPN covers the container's Firefox traffic. Every other app and your
machine's own browser keep their normal connection. This is an independent
project, with no affiliation to or endorsement from Proton AG.

## Requirements

- Linux with Python 3.11 or newer.
- Docker Engine running, plus Docker Compose v2.
- Your user must be able to run Docker.
- `/dev/net/tun` device available, including inside a virtual machine.
- A Proton VPN account and either OpenVPN credentials or a WireGuard `.conf` file.
- Extra disk space to pull and build the Docker images.

Linux x86_64 is the primary target. ARM64 depends on image availability.
Windows and macOS are not validated for this version.

The installer checks requirements; it does not install Docker or change your
machine's networking. On a VM, having web access by itself does not prove the
container's VPN tunnel can actually connect.

## Download and start

```sh
git clone https://github.com/drplagash/ProtonBrowserBox.git
cd ProtonBrowserBox
./setup.sh
```

You can also use **Code → Download ZIP**, extract the project and run
`sh setup.sh` from that folder.

The script installs the launcher, creates the private folders, lets you choose
the protocol and resources, stores credentials locally, and starts the VPN and
Firefox. If a configuration already exists, `./setup.sh` reuses it.

To go straight for OpenVPN TCP/443:

```sh
./setup.sh --openvpn-tcp
```

This mode needs no `.conf` or `.ovpn` download. It's the alternative that
worked during the project's manual testing on a VM where WireGuard never
reached a healthy state.

Once the terminal shows `Browser: READY`, open:

**[http://127.0.0.1:5800](http://127.0.0.1:5800)**

The page shows the Firefox session over noVNC; if a connection screen
appears, select **Connect**. Browse inside that Firefox session. If you chose
a different port, use the address the launcher printed. The first download or
image build can take several minutes.

## Finding your Proton credentials

### OpenVPN TCP/443

1. Open [account.protonvpn.com](https://account.protonvpn.com) and sign in
   with your regular Proton account.
2. Go to **Account** in the side menu.
3. Look for **OpenVPN username**. Some interfaces label this section
   **OpenVPN / IKEv2 username**.
4. Copy the **OpenVPN username** and **OpenVPN password** shown in that
   section.
5. Paste them when the script asks for `OpenVPN/IKEv2 username` and
   `OpenVPN/IKEv2 password`. The password is not echoed while typing or
   pasting.

**These are different from your Proton login email and password.** Each
person uses their own credentials.

Direct link to the panel: [account.protonvpn.com/account](https://account.protonvpn.com/account).
Official reference: [How to log in and find your OpenVPN username](https://protonvpn.com/support/vpn-login).

### WireGuard

1. Sign in at [account.protonvpn.com](https://account.protonvpn.com).
2. Go to **Downloads → WireGuard configuration**.
3. Pick a name, platform and a server your plan can reach. Select
   **Create**, then **Download** to get the `.conf` file.
4. Run `./setup.sh --wireguard`. When it asks for the folder, copy the file
   there and press Enter to continue.

The import folder is:

```text
ProtonBrowserBox/config/vpn/wireguard/
```

You can copy the file from your file manager or from the terminal:

```sh
cp ~/Downloads/your-proton-file.conf config/vpn/wireguard/
```

You don't need to run `chmod`: the project fixes permissions on its own. If
there's a single `.conf`, it's selected automatically; with several, you get
a list to choose from. If it contains a full peer, it uses that file's exact
server; if it only contains the private key, it uses Gluetun's Free server
selection.

Official reference: [Download WireGuard configurations](https://protonvpn.com/support/wireguard-configurations).

## Resources and profile

The `config` and `config --openvpn-tcp` wizards let you choose:

| Profile | Firefox RAM | Profile disk budget |
| --- | --- | --- |
| LIGHT | 1024 MB | 2048 MB |
| NORMAL | 2048 MB | 4096 MB |
| COMFORT | 4096 MB | 8192 MB |
| CUSTOM | Value you choose | Value you choose |

- **Persistent:** keeps the profile, cookies, history and sessions between runs.
- **Ephemeral:** uses a temporary profile that's deleted when you run `stop`.
- **Local web port:** `5800` by default. This is the local display port;
  OpenVPN still connects over TCP/443.
- **Resolution:** `1920x1080` by default; sets the container's desktop size.

Gluetun and the desktop use extra resources on top of Firefox's own. The disk
budget is checked before starting: it's not a Docker quota and doesn't
include images, layers or logs. Profiles are never auto-deleted to reclaim
space.

## Daily use and commands

Run these commands from the project folder. `./vpn-browser` with no
arguments is the same as `./vpn-browser start`. After `install.sh`, you can
also use plain `vpn-browser` if `~/.local/bin` is on your `PATH`.

| Command | What it does |
| --- | --- |
| `./vpn-browser` or `./vpn-browser start` | Starts Gluetun, waits for the VPN, then starts Firefox; prints the local URL. |
| `./vpn-browser stop` | Stops the containers and cleans up the ephemeral profile, if any. |
| `./vpn-browser status` | Shows protocol, resources, port, profile size, container health and whether secrets exist. |
| `./vpn-browser doctor` | Checks Docker, Compose, TUN, configuration, permissions, isolation layout and resources. Does not by itself prove the VPN can connect. |
| `./vpn-browser config` | Configures resources and re-imports WireGuard from the `.conf` folder. |
| `./vpn-browser config --openvpn-tcp` | Configures resources, port, profile and credentials for OpenVPN TCP/443. |
| `./vpn-browser server` | Menu to pick the VPN mode and server. |
| `./vpn-browser server --openvpn-tcp` | Switches to OpenVPN TCP/443 and asks for its credentials. Keeps existing resource settings; if none exist, uses the NORMAL profile. |
| `./vpn-browser server --auto` | Switches to WireGuard with automatic Proton Free server selection. Requires a previously imported WireGuard key. |
| `./vpn-browser server --country "United States"` | Switches to WireGuard and limits selection to a country with Free servers available in Gluetun. |
| `./vpn-browser server --exact` | Switches to the exact, previously imported WireGuard peer. Requires full peer data. |
| `./vpn-browser logs` | Shows the last 200 log lines from the services, with known secrets redacted. |
| `./vpn-browser logs --tail 50` | Limits how many log lines are shown. |
| `./vpn-browser --debug status` | Turns on diagnostic-level logging; `--debug` goes before the command. |
| `./vpn-browser clear-profile` | Asks you to type `DELETE PROFILE` before deleting the persistent profile. Run `stop` first. |
| `./vpn-browser reset` | Asks you to type `DELETE CONFIG` and removes settings and imported secrets, including OpenVPN credentials. Keeps the original `.conf` files and profiles. Run `stop` first. |
| `./vpn-browser version` | Shows the launcher's version. |
| `./vpn-browser --help` | Lists commands and options. |
| `./setup.sh` | Installs, configures and starts; reuses an existing configuration. |
| `./setup.sh --openvpn-tcp` | Forces a fresh, guided OpenVPN setup and starts. |
| `./setup.sh --wireguard` | Forces a fresh, guided WireGuard import and starts. |
| `./install.sh` | Checks requirements, creates folders and installs the `~/.local/bin/vpn-browser` shortcut; does not start the VPN. |
| `./uninstall.sh` | Removes the installed shortcut and asks whether to also delete configuration and data. Run `stop` first. |
| `scripts/network-diagnose.sh` | Tests host HTTPS, requirements, a UDP path and Gluetun's actual health. Stops the appliance when done; output may include IPs and endpoints. |

Protocol, server or configuration changes take effect on restart:

```sh
./vpn-browser stop
./vpn-browser server --openvpn-tcp
./vpn-browser
```

To adjust resources or the port while keeping OpenVPN, use
`./vpn-browser config --openvpn-tcp` with the containers stopped.
`server --auto`, `--country` and `--exact` select **WireGuard**, never OpenVPN
servers. Selection depends on whatever servers Proton and Gluetun offer at
that moment; a valid country name is no guarantee of availability.

## Local files and credentials

```text
config/vpn/
  settings.json                Machine settings, no password
  compose.override.yaml        Docker config generated by the launcher
  wireguard/                   Your .conf files downloaded from Proton
  secrets/
    wireguard_private_key      Imported WireGuard private key
    openvpn_user                Manual OpenVPN username
    openvpn_password            Manual OpenVPN password
  data/
    browser-profile/           Persistent profile
    ephemeral-browser-profile/ Temporary profile
```

The project creates private directories and secrets with restricted
permissions. Credential files are stored locally in plain text, protected by
file permissions; they are not encrypted on disk. `config/vpn/` is excluded
from Git, along with `.env`, logs and `.conf`, `.ovpn`, `.key` and `.pem`
files. Don't share or publish your whole working checkout: use the versioned
files or the project's clean ZIP instead.

For advanced setups, `VPN_BROWSER_CONFIG_DIR` and `VPN_BROWSER_DATA_DIR` let
you relocate the local paths. If you use paths outside the project, apply the
same variables to every command and don't add their files to Git.

## Common issues

### The VPN doesn't pass its health check

```sh
./vpn-browser doctor
./vpn-browser logs --tail 120
```

Startup waits up to 90 seconds for the VPN and up to 60 for the browser. An
unhealthy VPN keeps the launcher from starting the browser. If the logs show
`AUTH_FAILED`, check your **OpenVPN** credentials, not your email login.
If WireGuard won't connect, try OpenVPN TCP/443 or regenerate your `.conf`.

The official Proton app can work while the container fails: they may be
using a different protocol, server or route. To check this appliance's own
connection:

```sh
scripts/network-diagnose.sh
```

The UDP send test only confirms a local route exists; it doesn't prove the
server accepted the packet or that WireGuard can actually connect. Review
the diagnostic output and logs before sharing them — they can include IPs
and other details about your environment.

### Firefox says "Unable to connect" or "The connection was reset"

Confirm `Browser: READY` and check `./vpn-browser status`. Use
`http://127.0.0.1:5800`, or whatever port the launcher printed. `localhost`
can resolve to IPv6 while the appliance listens on IPv4. Running only
`config` saves settings; starting actually requires `./vpn-browser`.

### Port 6666 is restricted

Firefox blocks certain ports. Keep `5800` or pick another allowed, available
web port. There's no need to disable Firefox's own protection for this.

### Permissions, Docker or TUN

`./vpn-browser doctor` tells you which requirement is missing. If Docker
isn't accessible to your user, or the VM has no `/dev/net/tun`, that's a host
requirement you need to fix. The project manages permissions on its own
configuration files automatically.

## Scope and safety

- The launcher only manages its own containers and the files under `config/vpn/`. It does not install Docker or change your machine's networking.
- Credentials stay local, with restricted file permissions, and are never sent anywhere except to Proton through the VPN client. `config/vpn/` is excluded from Git.
- The web interface is published only on `127.0.0.1` and has no authentication; do not expose that port to the Internet or your LAN.
- Use it with your own Proton account and within Proton's terms of service.

## Known limitations

Early version, under active development. OpenVPN TCP/443 was tested manually
during development. Automated tests check code and the Compose structure;
they do not certify anonymity or the absence of leaks on every network.

Gluetun's firewall and the shared network namespace are what enforce the kill
switch. The interface is only published on `127.0.0.1` and has no web
authentication. Don't expose that port to the Internet or your LAN. The
automated tunnel-drop test script is still a pending placeholder.

## Development and tests

```sh
python3 -m pip install -e '.[dev]'
ruff check .
python3 -m pytest
scripts/smoke-test.sh
scripts/release-check.sh
```

`smoke-test.sh` runs the tests, validates Compose and builds the image.
`release-check.sh` adds whatever analysis tools are available and reports
which checks were skipped. Tests against a real Proton account need a
configuration:

```sh
VPN_BROWSER_PROTON_CONF=/private/path/proton.conf scripts/integration-test.sh
```

See [installation](docs/install.md), [troubleshooting](docs/troubleshooting.md),
[architecture](docs/architecture.md), [testing](docs/testing.md),
[security](docs/security.md) and [contributing](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).

## Author

DrPlaga
