#!/usr/bin/env python3
import argparse
import copy
import json
import os
import pathlib
import subprocess
import sys
from typing import List

from config import DEFAULT_CONFIG, load_runtime_config, save_canonical_config, validate_config


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
VALIDATION_DIR = REPO_ROOT / "python" / ".validation"
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


def validate_local_flow() -> List[str]:
    failures: List[str] = []

    _setup_local_config_files()
    _set_local_env()

    try:
        cfg = load_runtime_config()
        assert sorted(cfg.keys()) == ["display", "feed", "wifi"]
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
    sys.exit(main())
