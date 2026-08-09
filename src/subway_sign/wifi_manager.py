import json
import logging
import os
import pathlib
import shutil
import subprocess
import time

from cryptography.fernet import Fernet

from subway_sign.config import load_runtime_config


LOG = logging.getLogger(__name__)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

WPA_SUPPLICANT_CONF = pathlib.Path("/etc/wpa_supplicant/wpa_supplicant.conf")
DEV_WPA_SUPPLICANT_CONF = REPO_ROOT / "setup" / "wpa_supplicant.conf.dev"

KEY_FILE = pathlib.Path("/home/subwaysign/encryption.key")
DEV_KEY_FILE = REPO_ROOT / "setup" / "encryption.key"

PASSWORD_PREFIX = "enc:"
STATE_AP_ACTIVE = "ap_active"
STATE_TRANSITIONING = "transitioning_to_client"
STATE_CLIENT_ACTIVE = "client_active"
STATE_ROLLBACK = "rollback_to_ap"
STATE_FAILED = "failed"

ALLOWED_SERVICES = {"wpa_supplicant", "hostapd", "dnsmasq", "subway-sign", "web-config"}


def _prefer_path(primary: pathlib.Path, fallback: pathlib.Path) -> pathlib.Path:
    if primary.parent.exists() and os.access(primary.parent, os.W_OK):
        return primary
    fallback.parent.mkdir(parents=True, exist_ok=True)
    return fallback


def _resolve_key_path() -> pathlib.Path:
    return _prefer_path(KEY_FILE, DEV_KEY_FILE)


def _resolve_wpa_path() -> pathlib.Path:
    return _prefer_path(WPA_SUPPLICANT_CONF, DEV_WPA_SUPPLICANT_CONF)


def _run_command(command):
    return subprocess.run(command, check=False, capture_output=True, text=True)


def _set_owner_only_mode(path: pathlib.Path) -> None:
    try:
        os.chmod(path, 0o600)
    except OSError:
        LOG.warning("Could not set 0600 permissions on %s", path)


def load_key():
    key_file = _resolve_key_path()
    if not key_file.exists():
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key = Fernet.generate_key()
        with key_file.open("wb") as handle:
            handle.write(key)
        _set_owner_only_mode(key_file)
    else:
        with key_file.open("rb") as handle:
            key = handle.read()
    return Fernet(key)


cipher = load_key()


def encrypt_password(password):
    if not password:
        return ""
    if is_password_encrypted(password):
        return password
    token = cipher.encrypt(password.encode("utf-8")).decode("utf-8")
    return f"{PASSWORD_PREFIX}{token}"


def is_password_encrypted(value):
    return isinstance(value, str) and value.startswith(PASSWORD_PREFIX)


def decrypt_password(enc_password):
    if not enc_password:
        return ""
    token = enc_password
    if token.startswith(PASSWORD_PREFIX):
        token = token[len(PASSWORD_PREFIX):]
    return cipher.decrypt(token.encode("utf-8")).decode("utf-8")


def run_systemctl(action, service):
    if service not in ALLOWED_SERVICES:
        raise ValueError(f"Service {service} is not in the approved service allowlist")
    if action not in {"start", "stop", "restart"}:
        raise ValueError(f"Action {action} is not allowed")
    return _run_command(["sudo", "systemctl", action, service])


def _write_wpa_supplicant(ssid, password):
    wpa_path = _resolve_wpa_path()
    wpa_path.parent.mkdir(parents=True, exist_ok=True)
    content = (
        "ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\n"
        "update_config=1\n"
        "network={\n"
        f"    ssid=\"{ssid}\"\n"
        f"    psk=\"{password}\"\n"
        "}\n"
    )
    with wpa_path.open("w", encoding="utf-8") as handle:
        handle.write(content)
    _set_owner_only_mode(wpa_path)
    return wpa_path


def _wifi_connected_to_ssid(target_ssid):
    command = _run_command(["/sbin/iwgetid", "-r"])
    if command.returncode != 0:
        return False
    current_ssid = (command.stdout or "").strip()
    return current_ssid == target_ssid


def _wait_for_wifi(target_ssid, timeout_sec):
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        if _wifi_connected_to_ssid(target_ssid):
            return True
        time.sleep(2)
    return False


def _restore_ap_services():
    run_systemctl("start", "hostapd")
    run_systemctl("start", "dnsmasq")


def reset_to_ap_onboarding():
    wpa_path = _resolve_wpa_path()
    if wpa_path.exists():
        wpa_path.unlink()

    run_systemctl("stop", "subway-sign")
    run_systemctl("restart", "wpa_supplicant")
    _restore_ap_services()
    return {"ok": True, "state": STATE_AP_ACTIVE}


def transition_from_ap_to_client(ssid, password, timeout_sec=90):
    if not ssid or not password:
        return {"ok": False, "state": STATE_FAILED, "reason": "missing_ssid_or_password"}

    wpa_path = _resolve_wpa_path()
    backup_path = wpa_path.with_suffix(f"{wpa_path.suffix}.bak")
    current_state = STATE_AP_ACTIVE

    try:
        if wpa_path.exists():
            shutil.copy2(wpa_path, backup_path)

        current_state = STATE_TRANSITIONING
        _write_wpa_supplicant(ssid, password)
        run_systemctl("restart", "wpa_supplicant")

        if not _wait_for_wifi(ssid, timeout_sec):
            raise RuntimeError("Timed out waiting for client WiFi association")

        run_systemctl("stop", "hostapd")
        run_systemctl("stop", "dnsmasq")
        current_state = STATE_CLIENT_ACTIVE
        return {"ok": True, "state": current_state}
    except Exception as exc:
        current_state = STATE_ROLLBACK
        if backup_path.exists():
            shutil.copy2(backup_path, wpa_path)
            _set_owner_only_mode(wpa_path)
        run_systemctl("restart", "wpa_supplicant")
        _restore_ap_services()
        return {"ok": False, "state": current_state, "reason": str(exc)}
    finally:
        if backup_path.exists():
            try:
                backup_path.unlink()
            except OSError:
                LOG.warning("Failed to clean up temporary backup file: %s", backup_path)


def apply_runtime_sequence(config, restart_web_config=False, transition_timeout_sec=90):
    wifi = config.get("wifi", {})
    ssid = wifi.get("ssid", "").strip()
    stored_password = wifi.get("password", "")

    password = ""
    if stored_password:
        try:
            password = decrypt_password(stored_password)
        except Exception:
            LOG.warning("WiFi password decryption failed; treating credential as plaintext fallback")
            password = stored_password

    transition = transition_from_ap_to_client(ssid, password, timeout_sec=transition_timeout_sec)
    if not transition.get("ok"):
        return transition

    run_systemctl("restart", "subway-sign")
    if restart_web_config:
        run_systemctl("restart", "web-config")

    return transition


def main() -> int:
    result = apply_runtime_sequence(load_runtime_config())
    print(json.dumps(result))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
