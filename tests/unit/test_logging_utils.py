# Copyright (c) 2026 DrPlaga. Licencia MIT (ver LICENSE).

from vpn_browser.logging_utils import redact


def test_redacts_wireguard_environment_value() -> None:
    text = "WIREGUARD_PRIVATE_KEY=abc123"
    assert redact(text) == "WIREGUARD_PRIVATE_KEY=[REDACTED]"


def test_redacts_wireguard_config_private_key() -> None:
    text = "PrivateKey = abc123\nAddress = 10.2.0.2/32"
    assert "abc123" not in redact(text)
    assert "PrivateKey = [REDACTED]" in redact(text)


def test_redacts_gluetun_abbreviated_private_key() -> None:
    text = "Private key: abc...xyz="
    assert redact(text) == "Private key: [REDACTED]"


def test_redacts_extra_secret_exact_value() -> None:
    assert redact("token secret-value here", ["secret-value"]) == "token [REDACTED] here"
