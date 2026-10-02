# Author: DrPlaga

from vpn_browser.config import Settings
from vpn_browser.docker import COMPOSE_FILE, compose_env, prepare_compose_override
from vpn_browser.paths import get_paths


def test_compose_env_contains_runtime_paths(tmp_path) -> None:
    paths = get_paths({"HOME": str(tmp_path)})
    settings = Settings.default()
    env = compose_env(paths, settings)
    assert env["VPN_BROWSER_WIREGUARD_PRIVATE_KEY_FILE"] == str(paths.wireguard_private_key_file)
    assert env["VPN_BROWSER_PROFILE_DIR"] == str(paths.browser_profile_dir)
    assert env["VPN_BROWSER_WEB_PORT"] == "5800"
    assert env["VPN_BROWSER_BROWSER_MEMORY_MB"] == "2048"


def test_compose_env_uses_ephemeral_profile_when_configured(tmp_path) -> None:
    paths = get_paths({"HOME": str(tmp_path)})
    settings = Settings.default().__class__(
        persistent_browser_profile=False,
    )
    env = compose_env(paths, settings)
    assert env["VPN_BROWSER_PROFILE_DIR"] == str(paths.ephemeral_browser_profile_dir)


def test_compose_file_exists() -> None:
    assert COMPOSE_FILE.exists()


def test_manual_country_writes_compose_override(tmp_path) -> None:
    paths = get_paths({"HOME": str(tmp_path)})
    settings = Settings.default().__class__(
        country_mode="manual",
        country="United States",
        wireguard_endpoint_ip="95.173.217.71",
        wireguard_endpoint_port=51820,
        wireguard_public_key="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
        wireguard_addresses=["10.2.0.2/32"],
        wireguard_persistent_keepalive=25,
    )
    override = prepare_compose_override(paths, settings)
    assert override == paths.compose_override_file
    text = override.read_text(encoding="utf-8")
    assert 'SERVER_COUNTRIES: "United States"' in text
    assert "WIREGUARD_ENDPOINT_IP" not in text
    assert "WIREGUARD_ENDPOINT_PORT" not in text
    assert "WIREGUARD_ADDRESSES" not in text


def test_wireguard_implementation_writes_compose_override(tmp_path) -> None:
    paths = get_paths({"HOME": str(tmp_path)})
    settings = Settings.default().__class__(
        wireguard_implementation="userspace",
    )
    override = prepare_compose_override(paths, settings)
    assert override == paths.compose_override_file
    assert 'WIREGUARD_IMPLEMENTATION: "userspace"' in override.read_text(encoding="utf-8")


def test_custom_provider_writes_wireguard_compose_override(tmp_path) -> None:
    paths = get_paths({"HOME": str(tmp_path)})
    settings = Settings.default().__class__(
        provider_mode="custom",
        wireguard_endpoint_ip="95.173.217.71",
        wireguard_endpoint_port=51820,
        wireguard_public_key="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
        wireguard_addresses=["10.2.0.2/32"],
        wireguard_persistent_keepalive=25,
        wireguard_mtu=1280,
    )
    override = prepare_compose_override(paths, settings)
    assert override == paths.compose_override_file
    text = override.read_text(encoding="utf-8")
    assert "FREE_ONLY: null" in text
    assert 'VPN_SERVICE_PROVIDER: "custom"' in text
    assert 'WIREGUARD_ENDPOINT_IP: "95.173.217.71"' in text
    assert "WIREGUARD_ENDPOINT_PORT: 51820" in text
    assert 'WIREGUARD_PUBLIC_KEY: "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="' in text
    assert 'WIREGUARD_ADDRESSES: "10.2.0.2/32"' in text
    assert 'WIREGUARD_ALLOWED_IPS: "0.0.0.0/0"' in text
    assert 'WIREGUARD_PERSISTENT_KEEPALIVE_INTERVAL: "25s"' in text
    assert "WIREGUARD_MTU: 1280" in text


def test_openvpn_tcp_writes_compose_override_with_secrets(tmp_path) -> None:
    paths = get_paths({"HOME": str(tmp_path)})
    settings = Settings.default().__class__(
        vpn_protocol="openvpn",
        openvpn_protocol="tcp",
        openvpn_endpoint_port=443,
    )
    override = prepare_compose_override(paths, settings)
    assert override == paths.compose_override_file
    text = override.read_text(encoding="utf-8")
    assert 'VPN_TYPE: "openvpn"' in text
    assert 'OPENVPN_PROTOCOL: "tcp"' in text
    assert "OPENVPN_ENDPOINT_PORT: 443" in text
    assert 'OPENVPN_USER_SECRETFILE: "/run/secrets/openvpn_user"' in text
    assert 'OPENVPN_PASSWORD_SECRETFILE: "/run/secrets/openvpn_password"' in text
    assert "openvpn_user:" in text
    assert f'file: "{paths.openvpn_user_file}"' in text
    assert "openvpn_password:" in text
    assert f'file: "{paths.openvpn_password_file}"' in text


def test_automatic_country_removes_stale_override(tmp_path) -> None:
    paths = get_paths({"HOME": str(tmp_path)})
    paths.config_dir.mkdir(parents=True)
    paths.compose_override_file.write_text("stale", encoding="utf-8")
    assert prepare_compose_override(paths, Settings.default()) is None
    assert not paths.compose_override_file.exists()
