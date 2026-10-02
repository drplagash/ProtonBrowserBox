# Author: DrPlaga

from __future__ import annotations

import logging
import re
from collections.abc import Iterable

SECRET_PATTERNS = [
    re.compile(r"(?i)(WIREGUARD_PRIVATE_KEY\s*=\s*)([^,\s]+)"),
    re.compile(r"(?i)(PrivateKey\s*=\s*)([^,\n\r]+)"),
    re.compile(r"(?i)(Private key:\s*)([^,\n\r]+)"),
    re.compile(r"(?i)(OPENVPN_PASSWORD\s*=\s*)([^,\s]+)"),
]


def redact(text: object, extra_secrets: Iterable[str] | None = None) -> str:
    value = str(text)
    for secret in extra_secrets or ():
        if secret:
            value = value.replace(secret, "[REDACTED]")
    for pattern in SECRET_PATTERNS:
        value = pattern.sub(r"\1[REDACTED]", value)
    return value


class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return redact(super().format(record))


def configure_logging(debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO
    handler = logging.StreamHandler()
    handler.setFormatter(RedactingFormatter("%(levelname)s: %(message)s"))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
