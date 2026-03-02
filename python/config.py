import copy
import json
import logging
import os
import pathlib
import tempfile
from typing import Any, Dict, List, Optional

try:
    import toml
except ImportError:  # pragma: no cover - optional compatibility dependency
    toml = None


LOG = logging.getLogger(__name__)

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
CANONICAL_CONFIG_PATH = pathlib.Path("/etc/matrix_config.json")
DEFAULT_CANONICAL_CONFIG_PATH = pathlib.Path("/etc/matrix_config_default.json")
DEV_CANONICAL_CONFIG_PATH = REPO_ROOT / "setup" / "matrix_config.json"
DEV_DEFAULT_CONFIG_PATH = REPO_ROOT / "setup" / "matrix_config_default.json"
LEGACY_TOML_CONFIG_PATH = REPO_ROOT / "settings.toml"


DEFAULT_CONFIG: Dict[str, Dict[str, Any]] = {
    "wifi": {
        "ssid": "",
        "password": "",
    },
    "display": {
        "brightness": 100,
        "mta_directions": "N",
        "refresh_time_delay": 30,
        "adaptive_refresh_enabled": True,
        "adaptive_refresh_min_sec": 15,
        "adaptive_refresh_max_sec": 60,
        "adaptive_refresh_imminent_threshold_min": 5,
        "adaptive_refresh_far_threshold_min": 20,
        "realtime_feed_cadence_sec": 30,
        "stale_data_grace_sec": 120,
        "direction_mapping_rules": [],
        "rotate_trip_delay": 4,
        "screen_refresh_interval": 2,
        "minimum_arrival_minutes": 2,
        "maximum_arrival_minutes": 99,
        "led_rows": 32,
        "led_columns": 64,
        "led_chain_length": 1,
        "led_parallel": 1,
        "led_hardware_mapping": "adafruit-hat",
        "line_direction_max_length": 10,
        "route_symbol_backends": "image,font,text",
        "route_symbol_assets_dir": "assets/route_symbols",
        "route_symbol_max_asset_px": 10,
        "route_symbol_cache_limit": 128,
        "route_symbol_text_max_chars": 2,
        "route_symbol_aliases": {
            "5X": "5D",
            "6X": "6D",
            "7X": "7D",
            "FS": "SF",
            "FX": "FD",
            "GS": "S",
            "SI": "SIR",
        },
    },
    "feed": {
        "mta_routes": "F,G",
        "mta_stop": "7 Av",
        "mta_feed_base_url": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2F",
    },
    "gtfs_static_refresh": {
        "enabled": True,
        "request_timeout_sec": 30,
        "transition_window_hours": 168,
        "snapshot_retention_count": 8,
        "service_action": "restart",
        "alert_command": "",
        "sources": [
            [
                "base",
                "https://web.mta.info/developers/data/nyct/subway/google_transit.zip",
            ],
            [
                "supplemented",
                "https://web.mta.info/developers/data/nyct/subway/google_transit_supplemented.zip",
            ],
        ],
    },
}


LEGACY_TOML_TO_CANONICAL = {
    "MTA_ROUTES": ("feed", "mta_routes"),
    "MTA_STOP": ("feed", "mta_stop"),
    "MTA_DIRECTIONS": ("display", "mta_directions"),
    "REFRESH_TIME_DELAY": ("display", "refresh_time_delay"),
    "ROTATE_TRIP_DELAY": ("display", "rotate_trip_delay"),
    "SCREEN_REFRESH_INTERVAL": ("display", "screen_refresh_interval"),
    "MINIMUM_ARRIVAL_MINUTES": ("display", "minimum_arrival_minutes"),
    "MAXIMUM_ARRIVAL_MINUTES": ("display", "maximum_arrival_minutes"),
    "LED_ROWS": ("display", "led_rows"),
    "LED_COLUMNS": ("display", "led_columns"),
    "LED_CHAIN_LENGTH": ("display", "led_chain_length"),
    "LED_PARALLEL": ("display", "led_parallel"),
    "LED_HARDWARE_MAPPING": ("display", "led_hardware_mapping"),
    "LINE_DIRECTION_MAX_LENGTH": ("display", "line_direction_max_length"),
    "MTA_FEED_BASE_URL": ("feed", "mta_feed_base_url"),
}


def _deep_merge(base: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in incoming.items():
        if (
            key in merged
            and isinstance(merged[key], dict)
            and isinstance(value, dict)
        ):
            merged[key] = _deep_merge(merged[key], value)
            continue
        merged[key] = value
    return merged


def _runtime_config_path() -> pathlib.Path:
    env_path = os.environ.get("MATRIX_CONFIG_PATH")
    if env_path:
        return pathlib.Path(env_path)
    if CANONICAL_CONFIG_PATH.exists():
        return CANONICAL_CONFIG_PATH
    return DEV_CANONICAL_CONFIG_PATH


def _default_config_path() -> pathlib.Path:
    if DEFAULT_CANONICAL_CONFIG_PATH.exists():
        return DEFAULT_CANONICAL_CONFIG_PATH
    return DEV_DEFAULT_CONFIG_PATH


def _normalize_config(config: Dict[str, Any]) -> Dict[str, Any]:
    normalized = _deep_merge(DEFAULT_CONFIG, config)

    display = normalized["display"]
    feed = normalized["feed"]
    wifi = normalized["wifi"]
    refresh = normalized["gtfs_static_refresh"]

    int_fields = (
        "brightness",
        "refresh_time_delay",
        "adaptive_refresh_min_sec",
        "adaptive_refresh_max_sec",
        "adaptive_refresh_imminent_threshold_min",
        "adaptive_refresh_far_threshold_min",
        "realtime_feed_cadence_sec",
        "stale_data_grace_sec",
        "rotate_trip_delay",
        "screen_refresh_interval",
        "minimum_arrival_minutes",
        "maximum_arrival_minutes",
        "led_rows",
        "led_columns",
        "led_chain_length",
        "led_parallel",
        "line_direction_max_length",
        "route_symbol_max_asset_px",
        "route_symbol_cache_limit",
        "route_symbol_text_max_chars",
    )
    for field in int_fields:
        display[field] = int(display[field])
    display["adaptive_refresh_enabled"] = bool(display.get("adaptive_refresh_enabled", True))
    display["direction_mapping_rules"] = _normalize_direction_mapping_rules(display.get("direction_mapping_rules"))

    wifi["ssid"] = str(wifi.get("ssid", ""))
    wifi["password"] = str(wifi.get("password", ""))

    display["mta_directions"] = str(display.get("mta_directions", "")).upper()
    display["led_hardware_mapping"] = str(display.get("led_hardware_mapping", "")).strip()
    display["route_symbol_assets_dir"] = str(display.get("route_symbol_assets_dir", "")).strip() or "assets/route_symbols"
    display["route_symbol_backends"] = ",".join(_parse_route_symbol_backends(display.get("route_symbol_backends")))
    display["route_symbol_aliases"] = _normalize_route_symbol_aliases(display.get("route_symbol_aliases"))

    feed["mta_routes"] = str(feed.get("mta_routes", "")).upper()
    feed["mta_stop"] = str(feed.get("mta_stop", "")).strip()
    feed["mta_feed_base_url"] = str(feed.get("mta_feed_base_url", "")).strip()

    refresh["enabled"] = bool(refresh.get("enabled", True))
    refresh["request_timeout_sec"] = int(refresh.get("request_timeout_sec", 30))
    refresh["transition_window_hours"] = int(refresh.get("transition_window_hours", 168))
    refresh["snapshot_retention_count"] = int(refresh.get("snapshot_retention_count", 8))
    refresh["service_action"] = str(refresh.get("service_action", "restart")).strip().lower()
    refresh["alert_command"] = str(refresh.get("alert_command", "")).strip()

    normalized_sources = []
    for source in refresh.get("sources", []):
        if not isinstance(source, (list, tuple)) or len(source) != 2:
            continue
        normalized_sources.append([str(source[0]).strip(), str(source[1]).strip()])
    if normalized_sources:
        refresh["sources"] = normalized_sources
    else:
        refresh["sources"] = copy.deepcopy(DEFAULT_CONFIG["gtfs_static_refresh"]["sources"])

    return normalized


def _normalize_direction_mapping_rules(value: Any) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        return []

    normalized_rules: List[Dict[str, Any]] = []
    for index, rule in enumerate(value):
        if not isinstance(rule, dict):
            continue
        selectors = rule.get("match", {})
        if not isinstance(selectors, dict):
            selectors = {}

        normalized_selectors: Dict[str, str] = {}
        for key in ("route_id", "stop_id", "direction"):
            selector_value = selectors.get(key, "")
            cleaned = str(selector_value).strip()
            if not cleaned:
                continue
            normalized_selectors[key] = cleaned.upper() if key != "direction" else " ".join(cleaned.upper().split())

        normalized_rules.append(
            {
                "match": normalized_selectors,
                "label": str(rule.get("label", "")).strip(),
                "priority": int(rule.get("priority", 100)),
                "_index": index,
            }
        )

    return normalized_rules


def _parse_route_symbol_backends(value: Any) -> List[str]:
    if isinstance(value, str):
        tokens = [token.strip().lower() for token in value.split(",") if token.strip()]
    elif isinstance(value, (list, tuple)):
        tokens = [str(token).strip().lower() for token in value if str(token).strip()]
    else:
        tokens = []

    deduplicated: List[str] = []
    for token in tokens:
        if token not in deduplicated:
            deduplicated.append(token)
    return deduplicated or ["image", "font", "text"]


def _normalize_route_symbol_aliases(value: Any) -> Dict[str, str]:
    if not isinstance(value, dict):
        return {}

    normalized: Dict[str, str] = {}
    for raw_key, raw_value in value.items():
        key = "".join(str(raw_key or "").upper().split())
        target = "".join(str(raw_value or "").upper().split())
        if not key or not target:
            continue
        normalized[key] = target
    return normalized


def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    normalized = _normalize_config(config)

    display = normalized["display"]
    feed = normalized["feed"]
    refresh = normalized["gtfs_static_refresh"]

    if display["brightness"] < 0 or display["brightness"] > 100:
        raise ValueError("display.brightness must be between 0 and 100")
    if display["minimum_arrival_minutes"] < 0:
        raise ValueError("display.minimum_arrival_minutes must be >= 0")
    if display["adaptive_refresh_min_sec"] <= 0:
        raise ValueError("display.adaptive_refresh_min_sec must be > 0")
    if display["adaptive_refresh_max_sec"] < display["adaptive_refresh_min_sec"]:
        raise ValueError("display.adaptive_refresh_max_sec must be >= adaptive_refresh_min_sec")
    if display["adaptive_refresh_imminent_threshold_min"] < 0:
        raise ValueError("display.adaptive_refresh_imminent_threshold_min must be >= 0")
    if (
        display["adaptive_refresh_far_threshold_min"]
        < display["adaptive_refresh_imminent_threshold_min"]
    ):
        raise ValueError(
            "display.adaptive_refresh_far_threshold_min must be >= adaptive_refresh_imminent_threshold_min"
        )
    if display["realtime_feed_cadence_sec"] <= 0:
        raise ValueError("display.realtime_feed_cadence_sec must be > 0")
    if display["stale_data_grace_sec"] <= 0:
        raise ValueError("display.stale_data_grace_sec must be > 0")
    if display["maximum_arrival_minutes"] < display["minimum_arrival_minutes"]:
        raise ValueError("display.maximum_arrival_minutes must be >= minimum_arrival_minutes")
    if display["led_rows"] <= 0 or display["led_columns"] <= 0:
        raise ValueError("display.led_rows and display.led_columns must be > 0")
    if display["line_direction_max_length"] <= 0:
        raise ValueError("display.line_direction_max_length must be > 0")
    if display["route_symbol_max_asset_px"] <= 0:
        raise ValueError("display.route_symbol_max_asset_px must be > 0")
    if display["route_symbol_cache_limit"] <= 0:
        raise ValueError("display.route_symbol_cache_limit must be > 0")
    if display["route_symbol_text_max_chars"] <= 0:
        raise ValueError("display.route_symbol_text_max_chars must be > 0")
    for alias_key, alias_target in display.get("route_symbol_aliases", {}).items():
        if not alias_key or not alias_target:
            raise ValueError("display.route_symbol_aliases entries must define non-empty alias and target")
    backends = _parse_route_symbol_backends(display.get("route_symbol_backends"))
    supported_backends = {"image", "font", "text"}
    if not backends:
        raise ValueError("display.route_symbol_backends must define at least one backend")
    unsupported = [backend for backend in backends if backend not in supported_backends]
    if unsupported:
        raise ValueError(
            "display.route_symbol_backends contains unsupported backend(s): " + ",".join(unsupported)
        )
    selector_to_label: Dict[tuple, str] = {}
    for rule in display["direction_mapping_rules"]:
        if not rule["label"]:
            raise ValueError("display.direction_mapping_rules entries must define a non-empty label")
        if rule["priority"] < 0:
            raise ValueError("display.direction_mapping_rules entries must use priority >= 0")
        selector_key = tuple(sorted(rule["match"].items()))
        if selector_key in selector_to_label and selector_to_label[selector_key] != rule["label"]:
            raise ValueError(
                "display.direction_mapping_rules contains conflicting labels for identical match selectors"
            )
        selector_to_label[selector_key] = rule["label"]
    if not feed["mta_feed_base_url"]:
        raise ValueError("feed.mta_feed_base_url is required")
    if refresh["request_timeout_sec"] <= 0:
        raise ValueError("gtfs_static_refresh.request_timeout_sec must be > 0")
    if refresh["transition_window_hours"] < 0:
        raise ValueError("gtfs_static_refresh.transition_window_hours must be >= 0")
    if refresh["snapshot_retention_count"] < 2:
        raise ValueError("gtfs_static_refresh.snapshot_retention_count must be >= 2")
    if refresh["service_action"] not in {"restart", "reload", "none"}:
        raise ValueError("gtfs_static_refresh.service_action must be one of restart, reload, none")

    source_names = set()
    for source in refresh["sources"]:
        if not source[0] or not source[1]:
            raise ValueError("gtfs_static_refresh.sources entries must contain name and URL")
        source_names.add(source[0])
    if {"base", "supplemented"} - source_names:
        raise ValueError("gtfs_static_refresh.sources must include both 'base' and 'supplemented'")

    return normalized


def _load_json_config(path: pathlib.Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_toml_compat(path: pathlib.Path) -> Dict[str, Any]:
    if toml is None:
        raise RuntimeError("Legacy TOML compatibility requested but 'toml' package is not installed")
    with path.open("r", encoding="utf-8") as handle:
        legacy = toml.load(handle)

    migrated: Dict[str, Any] = copy.deepcopy(DEFAULT_CONFIG)
    for legacy_key, mapped in LEGACY_TOML_TO_CANONICAL.items():
        if legacy_key not in legacy:
            continue
        section, field = mapped
        migrated[section][field] = legacy[legacy_key]
    return migrated


def load_runtime_config(allow_toml_compat: bool = True) -> Dict[str, Any]:
    config_path = _runtime_config_path()
    if config_path.exists():
        return validate_config(_load_json_config(config_path))

    default_path = _default_config_path()
    if default_path.exists():
        LOG.warning("Canonical config missing at %s. Falling back to defaults at %s", config_path, default_path)
        return validate_config(_load_json_config(default_path))

    if allow_toml_compat and LEGACY_TOML_CONFIG_PATH.exists():
        LOG.warning(
            "Canonical config missing at %s; using legacy TOML compatibility path at %s. Migration required.",
            config_path,
            LEGACY_TOML_CONFIG_PATH,
        )
        return validate_config(_load_toml_compat(LEGACY_TOML_CONFIG_PATH))

    LOG.warning("No config files found. Falling back to embedded defaults.")
    return validate_config(copy.deepcopy(DEFAULT_CONFIG))


def save_canonical_config(config: Dict[str, Any], path: Optional[pathlib.Path] = None) -> pathlib.Path:
    target = path or _runtime_config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    normalized = validate_config(config)

    fd, temp_path = tempfile.mkstemp(prefix=f"{target.name}.", suffix=".tmp", dir=str(target.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(normalized, handle, indent=4)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, target)
    except Exception:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise

    return target
