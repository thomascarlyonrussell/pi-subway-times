import subprocess
import json
import os
from cryptography.fernet import Fernet

CONFIG_FILE = os.environ.get("MATRIX_CONFIG_PATH", "/etc/matrix_config.json")
KEY_FILE = "/home/subwaysign/encryption.key"

# Load or create an encryption key
def load_key():
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as key_file:
            key_file.write(key)
    else:
        with open(KEY_FILE, "rb") as key_file:
            key = key_file.read()
    return Fernet(key)

cipher = load_key()

def encrypt_password(password):
    return cipher.encrypt(password.encode()).decode()

def decrypt_password(enc_password):
    return cipher.decrypt(enc_password.encode()).decode()

# Load Config
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"wifi": {}}

# Apply WiFi Settings
def apply_wifi_settings():
    config = load_config()
    ssid = config["wifi"].get("ssid")
    stored_password = config["wifi"].get("password", "")
    password = ""
    if stored_password:
        try:
            password = decrypt_password(stored_password)
        except Exception:
            password = stored_password

    if ssid and password:
        with open("/etc/wpa_supplicant/wpa_supplicant.conf", "w") as f:
            f.write(f"""ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
network={{
    ssid="{ssid}"
    psk="{password}"
}}""")
        subprocess.run(["sudo", "systemctl", "restart", "wpa_supplicant"])

        # Disable AP Mode
        subprocess.run(["sudo", "systemctl", "stop", "hostapd"])
        subprocess.run(["sudo", "systemctl", "stop", "dnsmasq"])

if __name__ == "__main__":
    apply_wifi_settings()
