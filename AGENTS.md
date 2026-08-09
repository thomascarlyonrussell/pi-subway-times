# GitHub Copilot Instructions for pi-subway-times

This document tells the Copilot Chat assistant how to help developers work with the
`pi-subway-times` repository.  It explains the project's structure, how to build and
run the code, and outlines conventions and gotchas.

> 📁 **Location**: workspace root; Copilot Chat will load this automatically.

---

## 🧱 Quick project overview

- **Goal**: Drive an Adafruit 64×32 RGB LED matrix using a Raspberry Pi Zero 2 W to
  display real‑time MTA subway arrival times for a selected station.
- **Language**: Python 3.9
- **Hardware**: Raspberry Pi (Pi OS), Adafruit RGB Matrix Bonnet, RGB LED matrix,
  power supply, micro‑SD card.
- **Runtime environment**: normally run under `subwaysign` user; the display service
  currently runs as `root` due to GPIO/LED permissions.

Key code lives in `src/subway_sign/`:

| File | Role |
|------|------|
| `main.py` | Main loop / screen rendering (`subway-display`).
| `splash.py` | Early boot splash screen renderer (`subway-splash`).
| `trips.py` | GTFS static parsing & MTA real‑time feed processing.
| `display.py` | Color helpers.
| `web_config.py` | Flask-based web UI for configuration (`subway-web-config`).
| `wifi_manager.py` | Wi‑Fi credential management & AP mode logic.
| `gtfs_refresh.py` | Automated GTFS static data fetcher (`subway-gtfs-refresh`).
| `gtfs_bootstrap.py` | GTFS static status and bootstrap check (`subway-gtfs-bootstrap`).

Static GTFS snapshots under `/var/lib/subway-sign/gtfs-static` contain the stop and route lookup data. Provisioning downloads the initial snapshot before starting the display service.
`settings.toml` is the canonical configuration; a JSON copy (`/etc/matrix_config.json`)
is written by the web UI.

Development-only utilities live in `scripts/` and are neither deployed with the
sign services nor installed as commands:

- `console_emulator.py` renders a terminal preview without LED hardware.
- `vendor_route_symbols.py` normalizes manually obtained route-symbol PNGs.

---

## ⚙️ Setup & build

The project uses `uv` for dependency and environment management, declared in `pyproject.toml`.
Typical setup on a fresh Pi is automated by `setup/setup_subway_sign.sh`.

```bash
# on the Pi
wget https://raw.githubusercontent.com/tomrussell-willdan/pi-subway-times/main/setup/setup_subway_sign.sh
chmod +x setup_subway_sign.sh
sudo ./setup_subway_sign.sh
```

That script:

1. Installs `uv` and synchronizes the environment (`uv sync`).
2. Sets up systemd services (`subway-sign`, `web-config`, `gtfs-bootstrap`, `gtfs-static-refresh`).
3. Moves config files into place and clones the repo.

On a development machine:

```bash
uv sync
uv run pytest
```

---

## ▶️ Running the code

**Manual invocation** (for development):

```bash
sudo .venv/bin/subway-display
# or console emulator without hardware:
uv run python scripts/console_emulator.py
```

`sudo` is required when the matrix bonnets are attached; the driver requires
root permissions. On a dev box without hardware, run
`uv run python scripts/console_emulator.py`.

**Services**:

- `subway-splash.service` – early boot splash screen (`MTA SUBWAY / BOOTING...`).
- `subway-sign.service` – display daemon (runs as root!).
- `web-config.service` – Flask UI for editing Wi‑Fi and display settings.
- `gtfs-bootstrap.service` – GTFS bootstrap check.
- `gtfs-static-refresh.service` – GTFS static data scheduled refresh.

Use `systemctl {start,stop,status}` to control them.  Logs are accessible via
`journalctl -u subway-sign` (or `web-config`).

**Configuration**:

- Primary source: `settings.toml` in repo root or `/etc/matrix_config.json` if
discharged via the web UI.
- Web UI writes JSON to `/etc/matrix_config.json` and restarts the display service.
- Keep TOML & JSON in sync when editing manually.

---

## 🔧 Common tasks & samples

1. **Refresh route-symbol assets**: use `scripts/vendor_route_symbols.py` with a
  manually obtained `louh/mta-subway-bullets` checkout; see `assets/route_symbols/README.md`.
2. **Change refresh interval**: edit `settings.toml`, e.g. `update_interval_sec`.
3. **Debug real-time feed parsing**: sprinkle `print` statements or use
   `uv run python -m pdb -m subway_sign.trips` to replay a saved GTFS-realtime protobuf.
4. **Simulate AP mode**: remove Wi‑Fi credentials and run `uv run subway-web-config` –
   it will create an open access point.

---

## 📝 Conventions & gotchas

- **Root requirement**: the display code must run with elevated privileges;
  attempts to run as non‑root will fail during matrix initialization.  Be
  cautious when editing systemd units.
- **Dual configuration formats**: avoid editing only one source; the web UI
  overwrites `settings.toml` when it restarts the service.
- **Static GTFS snapshots** are device-local runtime data and are not checked in.
  Provisioning must complete an initial refresh before the sign or emulator can read
  stop, route, and trip metadata.
- **Automated tests**: suite lives under `tests/` and can be run with `uv run pytest`.
- Wi‑Fi AP password is hard‑coded in setup script (`SetupYourSign`).  Change if
  you intend to distribute hardware.
- HTTP Basic auth in `web_config.py` is currently commented out.

---

## ❓ When you need help ask Copilot Chat

Here are some example prompts you can type to Copilot Chat once this file is in
place:

- "How do I run the display script on my laptop without the LED hardware?"
- "Add support for the N/Q/R/W lines to the font map."
- "Explain why `sudo .venv/bin/subway-display` is required."
- "Generate a systemd service file snippet for the `subway-sign` service."
- "Where is the configuration stored and how can I change the refresh interval?"

These instructions are meant to help the assistant provide relevant, on‑target
advice.  They do not constrain the user; feel free to ignore sections that don't
apply.

---

*Last updated: 2026-08-09*