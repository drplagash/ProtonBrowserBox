# Author: DrPlaga

APP_NAME = "vpn-browser"
DISPLAY_NAME = "ProtonBrowserBox"
VERSION = "0.1.0"

SUPPORTED_SCHEMA_VERSION = 1
DEFAULT_WEB_PORT = 5800

RESOURCE_PROFILES = {
    "light": {"memory_limit_mb": 1024, "disk_budget_mb": 2048},
    "normal": {"memory_limit_mb": 2048, "disk_budget_mb": 4096},
    "comfort": {"memory_limit_mb": 4096, "disk_budget_mb": 8192},
}
