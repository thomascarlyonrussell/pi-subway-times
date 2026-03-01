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

Key code lives in `python/`:

| File | Role |
|------|------|
| `main.py` | Main loop / screen rendering.
| `trips.py` | GTFS static parsing & MTA real‑time feed processing.
| `display.py` | Color helpers.
| `web_config.py` | Flask-based web UI for configuration.
| `wifi_manager.py` | Wi‑Fi credential management & AP mode logic.

Static data (`data/*.txt`) contains GTFS files used for stop/route lookups.
`settings.toml` is the canonical configuration; a JSON copy (`/etc/matrix_config.json`)
is written by the web UI.

---

## ⚙️ Setup & build

The project doesn't have a build step; it relies on Python dependencies declared in
`requirements.txt`.  Typical setup on a fresh Pi is automated by
`setup/setup_subway_sign.sh`.

```bash
# on the Pi
wget https://raw.githubusercontent.com/tomrussell-willdan/pi-subway-times/main/setup/setup_subway_sign.sh
chmod +x setup_subway_sign.sh
sudo ./setup_subway_sign.sh
```

That script:

1. Installs Python packages (`pip3 install -r requirements.txt`).
2. Sets up systemd services (`subway-sign` & `web-config`).
3. Moves config files into place and clones the repo.

If you work on a desktop machine, install the Python deps manually and run the
scripts without the LED hardware (the `rgbmatrix` library will refuse to
initialize).

---

## ▶️ Running the code

**Manual invocation** (for development):

```bash
cd /path/to/repo/python
sudo python3 main.py
```

`sudo` is required when the matrix bonnets are attached; the driver requires
root permissions.  On a dev box without hardware, remove the `sudo` and/or stub
out the `rgbmatrix` imports.

**Services**:

- `subway-sign.service` – display daemon (runs as root!).
- `web-config.service` – Flask UI for editing Wi‑Fi and display settings.

Use `systemctl {start,stop,status}` to control them.  Logs are accessible via
`journalctl -u subway-sign` (or `web-config`).

**Configuration**:

- Primary source: `settings.toml` in repo root or `/etc/matrix_config.json` if
discharged via the web UI.
- Web UI writes JSON to `/etc/matrix_config.json` and restarts the display service.
- Keep TOML & JSON in sync when editing manually.

---

## 🔧 Common tasks & samples

1. **Add a new subway line icon**: extend the `FONT_MAP` in `display.py` and add a
   BDF font file to `fonts/`.
2. **Change refresh interval**: edit `settings.toml`, e.g. `update_interval_sec`.
3. **Debug real-time feed parsing**: sprinkle `print` statements or use
   `python -m pdb python/trips.py` to replay a saved GTFS-realtime protobuf.
4. **Simulate AP mode**: remove Wi‑Fi credentials and run `python/web_config.py` –
   it will create an open access point.

---

## 📝 Conventions & gotchas

- **Root requirement**: the display code must run with elevated privileges;
  attempts to run as non‑root will fail during matrix initialization.  Be
  cautious when editing systemd units.
- **Dual configuration formats**: avoid editing only one source; the web UI
  overwrites `settings.toml` when it restarts the service.
- **Static GTFS files** are checked in for offline development but should be
  refreshed periodically if the lease/stop data changes.
- **No automated tests**; expect manual verification.  Unit tests may be added in
  the future under `tests/` if automated CI is desired.
- Wi‑Fi AP password is hard‑coded in setup script (`SetupYourSign`).  Change if
  you intend to distribute hardware.
- HTTP Basic auth in `web_config.py` is currently commented out.

---

## ❓ When you need help ask Copilot Chat

Here are some example prompts you can type to Copilot Chat once this file is in
place:

- "How do I run the display script on my laptop without the LED hardware?"
- "Add support for the N/Q/R/W lines to the font map."
- "Explain why `sudo python main.py` is required."
- "Generate a systemd service file snippet for the `subway-sign` service."
- "Where is the configuration stored and how can I change the refresh interval?"

These instructions are meant to help the assistant provide relevant, on‑target
advice.  They do not constrain the user; feel free to ignore sections that don't
apply.

---

*Last updated: 2026-03-01*