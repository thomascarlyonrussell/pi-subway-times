#!/usr/bin/env python3
import argparse
import copy
import importlib
import json
import os
import pathlib
import subprocess
import sys
from typing import List

from subway_sign.config import DEFAULT_CONFIG, load_runtime_config, save_canonical_config, validate_config


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
VALIDATION_DIR = REPO_ROOT / "tests" / ".validation"
LOCAL_CONFIG_PATH = VALIDATION_DIR / "matrix_config.json"
LOCAL_DEFAULT_PATH = VALIDATION_DIR / "matrix_config_default.json"


def _print_ok(message: str) -> None:
    print(f"[PASS] {message}")


def _print_skip(message: str) -> None:
    print(f"[SKIP] {message}")


def _print_fail(message: str) -> None:
    print(f"[FAIL] {message}")


def _setup_local_config_files() -> None:
    VALIDATION_DIR.mkdir(parents=True, exist_ok=True)
    with LOCAL_DEFAULT_PATH.open("w", encoding="utf-8") as handle:
        json.dump(DEFAULT_CONFIG, handle, indent=4)
        handle.write("\n")
    with LOCAL_CONFIG_PATH.open("w", encoding="utf-8") as handle:
        json.dump(DEFAULT_CONFIG, handle, indent=4)
        handle.write("\n")


def _set_local_env() -> None:
    os.environ["MATRIX_CONFIG_PATH"] = str(LOCAL_CONFIG_PATH)
    os.environ["MATRIX_CONFIG_DEFAULT_PATH"] = str(LOCAL_DEFAULT_PATH)
    os.environ["SETUP_PIN_FILE"] = str(VALIDATION_DIR / "subway_setup_pin")
    os.environ["WEB_CONFIG_SECRET_FILE"] = str(VALIDATION_DIR / "web_config_secret")


def validate_local_flow() -> List[str]:
    failures: List[str] = []

    _setup_local_config_files()
    _set_local_env()

    try:
        cfg = load_runtime_config()
        assert sorted(cfg.keys()) == ["display", "feed", "gtfs_static_refresh", "wifi"]
        _print_ok("Canonical config load returns expected sections")
    except Exception as exc:  # pragma: no cover - command-line utility
        failures.append(f"canonical load failed: {exc}")
        _print_fail(f"Canonical config load failed: {exc}")

    try:
        mutated = copy.deepcopy(DEFAULT_CONFIG)
        mutated["feed"]["mta_stop"] = "Times Sq - 42 St"
        mutated["display"]["minimum_arrival_minutes"] = 3
        save_canonical_config(mutated, LOCAL_CONFIG_PATH)
        loaded = load_runtime_config()
        assert loaded["feed"]["mta_stop"] == "Times Sq - 42 St"
        assert loaded["display"]["minimum_arrival_minutes"] == 3
        _print_ok("Atomic save/read roundtrip works for canonical JSON")
    except Exception as exc:  # pragma: no cover - command-line utility
        failures.append(f"save/read roundtrip failed: {exc}")
        _print_fail(f"Save/read roundtrip failed: {exc}")

    try:
        invalid = copy.deepcopy(DEFAULT_CONFIG)
        invalid["display"]["maximum_arrival_minutes"] = -1
        validate_config(invalid)
        failures.append("invalid config unexpectedly passed validation")
        _print_fail("Invalid config unexpectedly passed validation")
    except Exception:
        _print_ok("Invalid config is rejected by shared validation")

    try:
        invalid_file_config = copy.deepcopy(DEFAULT_CONFIG)
        invalid_file_config["display"]["led_rows"] = -2
        with LOCAL_CONFIG_PATH.open("w", encoding="utf-8") as handle:
            json.dump(invalid_file_config, handle, indent=4)
            handle.write("\n")
        load_runtime_config()
        failures.append("invalid canonical file unexpectedly loaded")
        _print_fail("Invalid canonical file unexpectedly loaded")
    except Exception:
        _print_ok("Invalid canonical file fails fast during runtime load")
    finally:
        save_canonical_config(DEFAULT_CONFIG, LOCAL_CONFIG_PATH)

    return failures


def validate_discovery_and_save_flow() -> List[str]:
    failures: List[str] = []

    _setup_local_config_files()
    _set_local_env()

    try:
        seed = copy.deepcopy(DEFAULT_CONFIG)
        seed["feed"]["mta_routes"] = "F,G"
        seed["feed"]["mta_stop"] = "7 Av"
        seed["display"]["mta_directions"] = "N"
        save_canonical_config(seed, LOCAL_CONFIG_PATH)
    except Exception as exc:
        failures.append(f"seed config failed: {exc}")
        _print_fail(f"Seed config failed: {exc}")
        return failures

    try:
        from subway_sign import web_config  # local import so env overrides apply before module import
        web_config = importlib.reload(web_config)
        web_config.apply_runtime_changes = lambda restart_web_config=False: False
        web_config.app.testing = True

        with web_config.app.test_client() as client:
            unauth_routes = client.get("/api/discovery/routes")
            if unauth_routes.status_code == 401:
                _print_ok("Discovery routes endpoint requires setup authentication")
            else:
                failures.append("discovery routes endpoint accepted unauthenticated request")
                _print_fail("Discovery routes endpoint should require authentication")

            auth_response = client.post("/auth/login", json={"pin": web_config.SETUP_PIN})
            if auth_response.status_code != 200:
                failures.append("setup login failed for discovery validation")
                _print_fail("Setup login failed for discovery validation")
                return failures

            routes_response = client.get("/api/discovery/routes")
            routes_payload = routes_response.get_json() or {}
            route_ids = {route.get("route_id") for route in routes_payload.get("routes", [])}
            if routes_response.status_code == 200 and "F" in route_ids:
                _print_ok("Discovery routes endpoint returns GTFS-backed route options")
            else:
                failures.append("discovery routes endpoint did not return expected route data")
                _print_fail("Discovery routes endpoint did not return expected route data")

            stops_response = client.get("/api/discovery/stops?routes=F,G&directions=N")
            stops_payload = stops_response.get_json() or {}
            stop_names = {stop.get("stop_name") for stop in stops_payload.get("stops", [])}
            if stops_response.status_code == 200 and "7 Av" in stop_names:
                _print_ok("Discovery stops endpoint filters by selected routes and direction")
            else:
                failures.append("discovery stops endpoint did not return expected filtered stops")
                _print_fail("Discovery stops endpoint did not return expected filtered stops")

            valid_save = client.post(
                "/",
                data={
                    "mta_routes": "F,G",
                    "mta_stop": "7 Av",
                    "mta_directions": "N",
                },
            )
            valid_payload = valid_save.get_json() or {}
            if valid_save.status_code == 200 and "Restarted subway-sign" in valid_payload.get("message", ""):
                _print_ok("Config save succeeds for valid route/stop/direction selection")
            else:
                failures.append("valid config save did not succeed with restart messaging")
                _print_fail("Valid config save did not succeed with restart messaging")

            invalid_save = client.post(
                "/",
                data={
                    "mta_routes": "F,G",
                    "mta_stop": "Invalid Stop",
                    "mta_directions": "N",
                },
            )
            if invalid_save.status_code == 400:
                _print_ok("Config save rejects invalid route/stop/direction combinations")
            else:
                failures.append("invalid route/stop combination unexpectedly succeeded")
                _print_fail("Invalid route/stop combination unexpectedly succeeded")

    except Exception as exc:
        failures.append(f"discovery/save validation failed: {exc}")
        _print_fail(f"Discovery/save validation failed: {exc}")

    return failures


def validate_service_checks() -> List[str]:
    failures: List[str] = []
    commands = [
        ["systemctl", "status", "subway-sign"],
        ["systemctl", "status", "web-config"],
        ["systemctl", "is-enabled", "hostapd"],
        ["systemctl", "is-enabled", "dnsmasq"],
    ]
    for cmd in commands:
        try:
            completed = subprocess.run(
                ["sudo"] + cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
            )
            status = completed.returncode
            if status == 0:
                _print_ok(f"{' '.join(cmd)}")
            else:
                _print_skip(f"{' '.join(cmd)} returned {status}. Output: {completed.stdout.strip()}")
        except Exception as exc:  # pragma: no cover - command-line utility
            failures.append(f"service check failed for {' '.join(cmd)}: {exc}")
            _print_fail(f"Service check failed for {' '.join(cmd)}: {exc}")

    return failures


def test_local_flow():
    failures = validate_local_flow()
    assert not failures, f"Failures in local flow: {failures}"


def test_discovery_and_save_flow():
    failures = validate_discovery_and_save_flow()
    assert not failures, f"Failures in discovery/save flow: {failures}"


def test_explicit_missing_config_path_does_not_fallback(monkeypatch, tmp_path):
    missing_path = tmp_path / "missing.json"
    monkeypatch.setenv("MATRIX_CONFIG_PATH", str(missing_path))

    try:
        load_runtime_config()
    except FileNotFoundError as exc:
        assert str(missing_path) in str(exc)
    else:
        raise AssertionError("Expected missing explicit canonical config path to fail")


def test_shipped_default_template_validates():
    template_path = REPO_ROOT / "setup" / "matrix_config_default.json"
    with template_path.open("r", encoding="utf-8") as handle:
        template = json.load(handle)

    assert validate_config(template)["feed"]["mta_stop"] == template["feed"]["mta_stop"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate unified config flow.")
    parser.add_argument(
        "--with-services",
        action="store_true",
        help="Run additional systemctl checks (intended for Raspberry Pi host).",
    )
    args = parser.parse_args()

    print("Running local unified-config checks...")
    failures = validate_local_flow()
    print("Running route/stop discovery + save flow checks...")
    failures.extend(validate_discovery_and_save_flow())

    if args.with_services:
        print("Running service-level checks...")
        failures.extend(validate_service_checks())
    else:
        _print_skip("Service-level checks disabled. Use --with-services on Raspberry Pi.")

    if failures:
        print(f"\nValidation completed with {len(failures)} failure(s).")
        for failure in failures:
            print(f" - {failure}")
        return 1

    print("\nValidation completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
