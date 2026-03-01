from flask import Flask, render_template, request, jsonify
# from flask_httpauth import HTTPBasicAuth
import os
import json
import pathlib
import subprocess

import logging

from config import load_runtime_config, save_canonical_config, validate_config


LOG_FILE = "/var/log/subway_sign.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
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

## Authorization
# auth = HTTPBasicAuth()

# USERS = {"admin": "SecurePassword123"}

# @auth.verify_password
# def verify(username, password):
#     return USERS.get(username) == password


def load_config():
    return load_runtime_config(allow_toml_compat=True)


def save_config(config):
    return save_canonical_config(config, CONFIG_FILE)


def _to_int(form_data, key, fallback):
    value = form_data.get(key, fallback)
    return int(value)


def _apply_form(config, form_data):
    config = validate_config(config)
    config["wifi"]["ssid"] = form_data.get("ssid", config["wifi"]["ssid"])
    config["wifi"]["password"] = form_data.get("password", config["wifi"]["password"])

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

    config["feed"]["mta_routes"] = form_data.get("mta_routes", config["feed"]["mta_routes"])
    config["feed"]["mta_stop"] = form_data.get("mta_stop", config["feed"]["mta_stop"])
    config["feed"]["mta_feed_base_url"] = form_data.get("mta_feed_base_url", config["feed"]["mta_feed_base_url"])

    return validate_config(config)


def apply_runtime_changes(restart_web_config=False):
    log_event("info", "Applying updated settings: reconfigure wifi and restart services as needed.")
    subprocess.run(["sudo", "wpa_cli", "-i", "wlan0", "reconfigure"], check=False)

    log_event("info", "Restarting subway-sign service.")
    subprocess.run(["sudo", "systemctl", "restart", "subway-sign"], check=False)

    if restart_web_config:
        log_event("info", "Restarting web-config service (optional).")
        subprocess.run(["sudo", "systemctl", "restart", "web-config"], check=False)

    log_event("info", "Stopping hostapd and dnsmasq AP services.")
    subprocess.run(["sudo", "systemctl", "stop", "hostapd"], check=False)
    subprocess.run(["sudo", "systemctl", "stop", "dnsmasq"], check=False)

    return restart_web_config

@app.route("/", methods=["GET", "POST"])
# @auth.login_required
def index():
    config = validate_config(load_config())
    
    if request.method == "POST":
        try:
            next_config = _apply_form(config, request.form)
            log_event("info", f"User updated settings: {request.form.to_dict()}")
            save_config(next_config)
            restarted_web = apply_runtime_changes(
                restart_web_config=request.args.get("restart_web_config", "0") == "1"
            )
            msg = "Settings updated. Restarted subway-sign."
            if restarted_web:
                msg += " Restarted web-config."
            else:
                msg += " web-config restart not required."
            return jsonify({"message": msg})
        except Exception as exc:
            log_event("error", f"Failed to apply settings: {exc}")
            return jsonify({"message": f"Failed to apply settings: {exc}"}), 400

    return render_template("index.html", config=config)

@app.route("/reset", methods=["POST"])
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
    subprocess.run(["sudo", "systemctl", "restart", "subway-sign"], check=False)

    return jsonify({"message": "Factory reset complete. Restarting..."})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
    # app.run(host="0.0.0.0", port=5000, ssl_context=("cert.pem", "key.pem"))  # https
    # app.run(host="127.0.0.1", port=5000) #local connections only
