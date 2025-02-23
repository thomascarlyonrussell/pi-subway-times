from flask import Flask, render_template, request, jsonify
import json, os
import pathlib
import subprocess

import logging
from datetime import datetime
import os
import subprocess

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
config_path = pathlib.Path(__file__).parent.parent / "setup" / "matrix_config.json"
config_path_default = config_path.parent / "matrix_config_default.json"
CONFIG_FILE = config_path.absolute()
CONFIG_PATH_DEFAULT = config_path_default.absolute()
TEMPLATE_FILE = template_path.absolute()

app = Flask(__name__,template_folder=TEMPLATE_FILE)

def load_config():
    if os.path.exists(str(CONFIG_FILE)):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"wifi": {}, "display": {}, "feed": {}}

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

@app.route("/", methods=["GET", "POST"])
def index():
    config = load_config()
    
    if request.method == "POST":
        config["wifi"]["ssid"] = request.form["ssid"]
        config["wifi"]["password"] = request.form["password"]
        
        config["display"]["brightness"] = int(request.form["brightness"])
        config["display"]["mta_directions"] = request.form["mta_directions"]
        config["display"]["refresh_time_delay"] = int(request.form["refresh_time_delay"])
        config["display"]["rotate_trip_delay"] = int(request.form["rotate_trip_delay"])
        config["display"]["screen_refresh_interval"] = int(request.form["screen_refresh_interval"])
        config["display"]["minimum_arrival_minutes"] = int(request.form["minimum_arrival_minutes"])
        config["display"]["maximum_arrival_minutes"] = int(request.form["maximum_arrival_minutes"])
        config["display"]["led_rows"] = int(request.form["led_rows"])
        config["display"]["led_columns"] = int(request.form["led_columns"])
        config["display"]["led_chain_length"] = int(request.form["led_chain_length"])
        config["display"]["led_parallel"] = int(request.form["led_parallel"])
        config["display"]["led_hardware_mapping"] = request.form["led_hardware_mapping"]
        config["display"]["line_direction_max_length"] = int(request.form["line_direction_max_length"])

        config["feed"]["mta_routes"] = request.form["mta_routes"]
        config["feed"]["mta_stop"] = request.form["mta_stop"]
        config["feed"]["mta_feed_base_url"] = request.form["mta_feed_base_url"]

        if request.method == "POST":
            log_event("info", f"User updated settings: {request.form.to_dict()}")
            save_config(config)

            # Restart the display service
            log_event("info", "Restarting wifi...")
            subprocess.Popen(["sudo", "wpa_cli", "-i", "wlan0", "reconfigure"])
            log_event("info", "Restarting subway sign service...")
            subprocess.Popen(["sudo", "systemctl", "restart", "subway-sign"])

        return jsonify({"message": "Settings updated! Restarting..."})

    return render_template("index.html", config=config)

@app.route("/reset", methods=["POST"])
def reset_to_defaults():
    
    log_event("warning", "Factory reset initiated via web interface.")

    if os.path.exists(CONFIG_PATH_DEFAULT):
        os.system(f"cp {CONFIG_PATH_DEFAULT} {CONFIG_FILE}")
        log_event("info", "Factory settings restored.")
    else:
        log_event("error", "Default settings file missing!")
        return jsonify({"message": "Default settings file missing!"}), 500

    # Restart the application
    log_event("info", "Restarting system after factory reset...")
    subprocess.Popen(["sudo", "systemctl", "restart", "subway-sign"])

    return jsonify({"message": "Factory reset complete. Restarting..."})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
