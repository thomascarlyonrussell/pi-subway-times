from flask import Flask, jsonify, render_template, request, session
import os
import json
import pathlib
import secrets
import time
from functools import wraps

import logging

from config import load_runtime_config, save_canonical_config, validate_config
from trips import (
    get_discoverable_routes,
    get_discoverable_stops,
    get_discovery_metadata,
    validate_route_stop_selection,
)
from wifi_manager import apply_runtime_sequence, encrypt_password, run_systemctl


LOG_FILE = "/var/log/subway_sign.log"
LOG_FILE_FALLBACK = pathlib.Path(__file__).resolve().parent.parent / "setup" / "subway_sign.log"
SENSITIVE_FIELDS = {"password", "psk", "secret", "token", "pin"}

try:
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
except OSError:
    logging.basicConfig(
        filename=str(LOG_FILE_FALLBACK),
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

def log_event(level, message):
    logging.log(getattr(logging, level.upper(), logging.INFO), message)

template_path = pathlib.Path(__file__).parent.parent / "templates"
config_path = pathlib.Path(os.environ.get("MATRIX_CONFIG_PATH", "/etc/matrix_config.json"))
config_path_default = pathlib.Path(os.environ.get("MATRIX_CONFIG_DEFAULT_PATH", "/etc/matrix_config_default.json"))
if not config_path.parent.exists():
    config_path = pathlib.Path(__file__).parent.parent / "setup" / "matrix_config.json"
if not config_path_default.parent.exists():
    config_path_default = pathlib.Path(__file__).parent.parent / "setup" / "matrix_config_default.json"

CONFIG_FILE = config_path.absolute()
CONFIG_PATH_DEFAULT = config_path_default.absolute()
TEMPLATE_FILE = template_path.absolute()
os.environ["MATRIX_CONFIG_PATH"] = str(CONFIG_FILE)
os.environ["MATRIX_CONFIG_DEFAULT_PATH"] = str(CONFIG_PATH_DEFAULT)

app = Flask(__name__,template_folder=TEMPLATE_FILE)

SESSION_TTL_SEC = int(os.environ.get("SETUP_SESSION_TTL_SEC", "900"))
SETUP_PIN_FILE = pathlib.Path(os.environ.get("SETUP_PIN_FILE", "/etc/subway_setup_pin"))
if not os.access(SETUP_PIN_FILE.parent, os.W_OK):
    SETUP_PIN_FILE = pathlib.Path(__file__).resolve().parent.parent / "setup" / "subway_setup_pin"
SECRET_FILE_DEFAULT = pathlib.Path(os.environ.get("WEB_CONFIG_SECRET_FILE", "/etc/web_config_secret"))
if not os.access(SECRET_FILE_DEFAULT.parent, os.W_OK):
    SECRET_FILE_DEFAULT = pathlib.Path(__file__).resolve().parent.parent / "setup" / "web_config_secret"


def _set_owner_only_mode(path):
    try:
        os.chmod(path, 0o600)
    except OSError:
        log_event("warning", f"Could not set secure file permissions for {path}")


def _load_or_create_secret(path):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        secret = secrets.token_hex(32)
        path.write_text(secret, encoding="utf-8")
        _set_owner_only_mode(path)
        return secret
    return path.read_text(encoding="utf-8").strip()


def _resolve_setup_pin():
    env_pin = os.environ.get("SUBWAY_SETUP_PIN")
    if env_pin:
        return env_pin
    if not SETUP_PIN_FILE.exists():
        pin = secrets.token_hex(4)
        SETUP_PIN_FILE.parent.mkdir(parents=True, exist_ok=True)
        SETUP_PIN_FILE.write_text(pin, encoding="utf-8")
        _set_owner_only_mode(SETUP_PIN_FILE)
        log_event("warning", "Generated onboarding setup PIN file; rotate after first use.")
        return pin
    return SETUP_PIN_FILE.read_text(encoding="utf-8").strip()


def _redact_sensitive(value):
    if isinstance(value, dict):
        redacted = {}
        for key, nested_value in value.items():
            if any(fragment in key.lower() for fragment in SENSITIVE_FIELDS):
                redacted[key] = "***REDACTED***"
            else:
                redacted[key] = _redact_sensitive(nested_value)
        return redacted
    if isinstance(value, list):
        return [_redact_sensitive(item) for item in value]
    return value


def _sanitize_public_config(config):
    sanitized = validate_config(config)
    if "wifi" in sanitized:
        sanitized["wifi"]["password"] = ""
    return sanitized


def _session_authenticated():
    if not session.get("setup_authenticated"):
        return False
    auth_time = session.get("setup_auth_time", 0)
    if (time.time() - auth_time) > SESSION_TTL_SEC:
        session.clear()
        return False
    return True


def require_setup_session(handler):
    @wraps(handler)
    def wrapper(*args, **kwargs):
        if not _session_authenticated():
            return jsonify({"message": "Setup authentication required"}), 401
        return handler(*args, **kwargs)

    return wrapper


app.secret_key = os.environ.get("WEB_CONFIG_SECRET_KEY") or _load_or_create_secret(SECRET_FILE_DEFAULT)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Strict"
app.config["PERMANENT_SESSION_LIFETIME"] = SESSION_TTL_SEC
if os.environ.get("WEB_CONFIG_SECURE_COOKIE", "0") == "1":
    app.config["SESSION_COOKIE_SECURE"] = True
SETUP_PIN = _resolve_setup_pin()


def load_config():
    return load_runtime_config(allow_toml_compat=True)


def save_config(config):
    return save_canonical_config(config, CONFIG_FILE)


def _to_int(form_data, key, fallback):
    value = form_data.get(key, fallback)
    return int(value)


def _normalize_route_list(raw_routes):
    if raw_routes is None:
        return []
    if isinstance(raw_routes, str):
        tokens = raw_routes.split(",")
    else:
        tokens = raw_routes
    normalized = []
    for token in tokens:
        cleaned = str(token).strip().upper()
        if cleaned and cleaned not in normalized:
            normalized.append(cleaned)
    return normalized


def _extract_routes(form_data, config):
    selected_routes = _normalize_route_list(form_data.getlist("mta_routes")) if hasattr(form_data, "getlist") else []
    if len(selected_routes) == 1 and "," in selected_routes[0]:
        selected_routes = _normalize_route_list(selected_routes[0])
    if not selected_routes:
        selected_routes = _normalize_route_list(form_data.get("mta_routes", config["feed"]["mta_routes"]))
    return ",".join(selected_routes)


def _apply_form(config, form_data):
    config = validate_config(config)
    config["wifi"]["ssid"] = form_data.get("ssid", config["wifi"]["ssid"])
    submitted_password = form_data.get("password", "")
    if submitted_password:
        config["wifi"]["password"] = encrypt_password(submitted_password)
    else:
        config["wifi"]["password"] = config["wifi"]["password"]

    config["display"]["brightness"] = _to_int(form_data, "brightness", config["display"]["brightness"])
    config["display"]["mta_directions"] = form_data.get("mta_directions", config["display"]["mta_directions"])
    config["display"]["refresh_time_delay"] = _to_int(form_data, "refresh_time_delay", config["display"]["refresh_time_delay"])
    config["display"]["rotate_trip_delay"] = _to_int(form_data, "rotate_trip_delay", config["display"]["rotate_trip_delay"])
    config["display"]["screen_refresh_interval"] = _to_int(form_data, "screen_refresh_interval", config["display"]["screen_refresh_interval"])
    config["display"]["minimum_arrival_minutes"] = _to_int(form_data, "minimum_arrival_minutes", config["display"]["minimum_arrival_minutes"])
    config["display"]["maximum_arrival_minutes"] = _to_int(form_data, "maximum_arrival_minutes", config["display"]["maximum_arrival_minutes"])
    config["display"]["led_rows"] = _to_int(form_data, "led_rows", config["display"]["led_rows"])
    config["display"]["led_columns"] = _to_int(form_data, "led_columns", config["display"]["led_columns"])
    config["display"]["led_chain_length"] = _to_int(form_data, "led_chain_length", config["display"]["led_chain_length"])
    config["display"]["led_parallel"] = _to_int(form_data, "led_parallel", config["display"]["led_parallel"])
    config["display"]["led_hardware_mapping"] = form_data.get("led_hardware_mapping", config["display"]["led_hardware_mapping"])
    config["display"]["line_direction_max_length"] = _to_int(form_data, "line_direction_max_length", config["display"]["line_direction_max_length"])

    config["feed"]["mta_routes"] = _extract_routes(form_data, config)
    config["feed"]["mta_stop"] = form_data.get("mta_stop", config["feed"]["mta_stop"]).strip()
    config["feed"]["mta_feed_base_url"] = form_data.get("mta_feed_base_url", config["feed"]["mta_feed_base_url"])

    validate_route_stop_selection(
        config["feed"]["mta_routes"],
        config["feed"]["mta_stop"],
        config["display"]["mta_directions"],
    )

    return validate_config(config)


def apply_runtime_changes(restart_web_config=False):
    log_event("info", "Applying updated settings: reconfigure wifi and restart services as needed.")
    result = apply_runtime_sequence(
        config=load_config(),
        restart_web_config=restart_web_config,
        transition_timeout_sec=int(os.environ.get("AP_TRANSITION_TIMEOUT_SEC", "90")),
    )
    if not result.get("ok"):
        reason = result.get("reason", "unknown error")
        log_event("error", f"WiFi onboarding transition failed: {reason}")
        raise RuntimeError(f"WiFi onboarding transition failed: {reason}")
    log_event("info", "Applied runtime service sequence successfully.")
    return restart_web_config

@app.route("/", methods=["GET", "POST"])
def index():
    config = validate_config(load_config())
    
    if request.method == "POST":
        if not _session_authenticated():
            return jsonify({"message": "Setup authentication required"}), 401
        try:
            next_config = _apply_form(config, request.form)
            log_event("info", f"User updated settings: {_redact_sensitive(request.form.to_dict())}")
            save_config(next_config)
            restarted_web = apply_runtime_changes(
                restart_web_config=request.args.get("restart_web_config", "0") == "1"
            )
            msg = "Settings updated. Restarted subway-sign to apply route/stop changes."
            if restarted_web:
                msg += " Restarted web-config."
            else:
                msg += " web-config restart not required."
            return jsonify({"message": msg})
        except Exception as exc:
            log_event("error", f"Failed to apply settings: {exc}")
            return jsonify({"message": f"Failed to apply settings: {exc}"}), 400

    return render_template("index.html", config=_sanitize_public_config(config))

@app.route("/reset", methods=["POST"])
@require_setup_session
def reset_to_defaults():
    
    log_event("warning", "Factory reset initiated via web interface.")

    if os.path.exists(CONFIG_PATH_DEFAULT):
        try:
            with open(CONFIG_PATH_DEFAULT, "r", encoding="utf-8") as default_file:
                config = validate_config(json.load(default_file))
            save_canonical_config(config, CONFIG_FILE)
            log_event("info", "Factory settings restored.")
        except Exception as exc:
            log_event("error", f"Factory reset failed: {exc}")
            return jsonify({"message": f"Factory reset failed: {exc}"}), 500
    else:
        log_event("error", "Default settings file missing!")
        return jsonify({"message": "Default settings file missing!"}), 500

    # Restart the application
    log_event("info", "Restarting system after factory reset...")
    run_systemctl("restart", "subway-sign")

    return jsonify({"message": "Factory reset complete. Restarting..."})


@app.route("/auth/login", methods=["POST"])
def auth_login():
    pin = request.form.get("pin") if request.form else None
    if pin is None and request.is_json:
        payload = request.get_json(silent=True) or {}
        pin = payload.get("pin")

    if not pin:
        return jsonify({"message": "PIN is required"}), 400
    if pin != SETUP_PIN:
        log_event("warning", "Failed setup login attempt")
        return jsonify({"message": "Invalid PIN"}), 401

    session["setup_authenticated"] = True
    session["setup_auth_time"] = time.time()
    return jsonify({"message": "Authenticated", "ttl_sec": SESSION_TTL_SEC})


@app.route("/auth/logout", methods=["POST"])
def auth_logout():
    session.clear()
    return jsonify({"message": "Logged out"})


@app.route("/auth/status", methods=["GET"])
def auth_status():
    return jsonify(
        {
            "authenticated": _session_authenticated(),
            "ttl_sec": SESSION_TTL_SEC,
        }
    )


@app.route("/api/discovery/routes", methods=["GET"])
@require_setup_session
def discovery_routes():
    metadata = get_discovery_metadata()
    return jsonify(
        {
            "generated_at_epoch": metadata["generated_at_epoch"],
            "routes": get_discoverable_routes(),
        }
    )


@app.route("/api/discovery/stops", methods=["GET"])
@require_setup_session
def discovery_stops():
    routes = _normalize_route_list(request.args.getlist("routes"))
    if len(routes) == 1 and "," in routes[0]:
        routes = _normalize_route_list(routes[0])
    directions = request.args.get("directions", "")
    return jsonify(
        {
            "filters": {
                "routes": routes,
                "directions": directions,
            },
            "stops": get_discoverable_stops(routes, directions),
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
    # app.run(host="0.0.0.0", port=5000, ssl_context=("cert.pem", "key.pem"))  # https
    # app.run(host="127.0.0.1", port=5000) #local connections only
