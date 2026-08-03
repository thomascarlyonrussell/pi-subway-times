# MTA Subway Times Display

## Hardware 
- Raspberry Pi Zero 2 W
- Adafruit RGB Matrix Bonnet
- Adafruit 64x32 RGB LED Matrix
- 5V 4A Power Supply
- MicroSD Card

## Software
- RaspbianPI OS
- Python 3.9

## Setup
### 1. Install Raspbian
1. Download the latest Raspbian image from the official website: https://www.raspberrypi.org/downloads/raspbian/
2. Write the image to the SD card using Etcher: https://etcher.io/
3. Insert the SD card into the Raspberry Pi and boot it up.
4. Follow the on-screen instructions to set up the system.
5. Update the system by running the shell script

```bash
wget https://raw.githubusercontent.com/tomrussell-willdan/pi-subway-times/refs/heads/main/setup/setup_subway_sign.sh
mv setup_subway_sign.sh?token=XYZ123 setup_subway_sign.sh
chmod +x setup_subway_sign.sh
sudo ./setup_subway_sign.sh
```

### Update and Configure Bonnet
1. Update the Bonnet by running the following command:
```bash
curl -fLO https://raw.githubusercontent.com/adafruit/Raspberry-Pi-Installer-Scripts/main/rgb-matrix.py
sudo /usr/bin/python3 rgb-matrix.py
```

The Adafruit installer changes boot and driver configuration. Do not rerun it
on a working prototype just to update this project; use it only when setting up
the RGB Matrix Bonnet/HAT or repairing its driver installation.


### Run the Program
1. SSH into the Raspberry Pi by running the following command:
```bash
ssh pi@raspberrypi.local
```
2. Run the program by running the following command:
```bash
cd "repos/pi-subway-times"
sudo python "pizero/src/main.py"
```
2. The program will start running and display the output on the screen.
3. Press `Ctrl + C` to stop the program.

### Setup Startup Script
This is a more robust way to start a script on boot.

Create a new service file:
bash
```sudo nano /etc/systemd/system/myscript.service```

Save and exit (CTRL + X, then Y, then ENTER).
Enable the service so it starts on boot:
Start the service manually to test:
Check status:
Reboot and verify:

```bash
sudo systemctl enable myscript.service
sudo systemctl start myscript.service 
sudo systemctl status myscript.service
sudo reboot
```

### Setup Web SErvice Startup 

#### Store Settings (Canonical Source)

`/etc/matrix_config.json` is the single source of truth.
`/etc/matrix_config_default.json` is the rollback/default template.

Legacy `settings.toml` is compatibility-only during migration and is no longer the preferred runtime source.

#### Store Wifi Hotspot Settings

`/etc/hostapd/hostapd.conf`

```bash
sudo systemctl enable web-config.service
sudo systemctl start web-config.service 
sudo systemctl status web-config.service
sudo reboot
```

- On boot, check if the device is connected to WiFi.
- If WiFi is not connected, enable AP mode and start the Flask web server.
- Users connect to the SubwaySign-Setup network and access the web UI at http://192.168.4.1:5000.
- After entering their details, the app atomically saves canonical JSON, restarts `subway-sign`, reconfigures Wi-Fi, and tears down AP services.


### Rotate Logs

```bash
sudo nano /etc/logrotate.d/subway-sign
```

```bash
/var/log/subway-sign/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 root root
    sharedscripts
    postrotate
        systemctl restart subway-sign
    endscript
}
```

### Validate Unified Config Flow

Run local config-flow checks:

```bash
python3 python/validate_config_flow.py
```

Run full checks on Raspberry Pi (includes service status checks):

```bash
python3 python/validate_config_flow.py --with-services
```

### Console Emulator

On a development machine, preview the sign's logical arrival rows without Raspberry Pi LED hardware, root access, or a systemd service:

```bash
python3 python/console_emulator.py
```

Use `Ctrl + C` to stop it. The emulator loads the same runtime configuration as the sign. To test another canonical JSON configuration without changing the system configuration, set `MATRIX_CONFIG_PATH` before launch:

```bash
MATRIX_CONFIG_PATH=/path/to/matrix_config.json python3 python/console_emulator.py
```

The emulator requests live MTA data through the production trip pipeline, so it needs network access, an active static GTFS snapshot, and the Python dependencies in `requirements.txt`. Create a snapshot with `python3 python/gtfs_refresh.py --force` before using the emulator on a fresh checkout. It displays logical route, direction, arrival, refresh, and error state only; it does not reproduce LED pixels, fonts, colors, symbols, GPIO behavior, or hardware refresh timing.

### Static GTFS Refresh

The project now supports static GTFS refresh with dual-source merge:
- Base archive: `google_transit.zip`
- Supplement archive: `google_transit_supplemented.zip` (overrides base on key collisions)

Refresh state and snapshots are stored under `/var/lib/subway-sign/gtfs-static` (or `setup/gtfs_static_state` fallback in dev).
The Pi defaults to retaining the active snapshot and one rollback snapshot. If an existing Pi configuration still sets `snapshot_retention_count` to `8`, change it to `2` in `/etc/matrix_config.json` to avoid consuming roughly 1.2 GB of SD-card storage.

On first setup, or when the active snapshot is missing, `gtfs-bootstrap.service` shows `SETUP`, `DOWNLOAD`, `UNPACK`, `STATIONS`, and `FINALIZE` status on the LED matrix before the live arrival display starts. A refresh failure leaves `FAILED` visible briefly and prevents the live display from starting without data. Normal boots with a valid snapshot start arrivals directly; scheduled refreshes remain headless so they do not interrupt the sign.

Manual forced refresh:

```bash
python3 python/gtfs_refresh.py --force
```

Manual visual bootstrap, useful after intentionally removing an invalid or legacy state pointer:

```bash
sudo python3 python/gtfs_bootstrap.py --force
```

Manual rollback to previous snapshot:

```bash
python3 python/gtfs_refresh.py --rollback
```

Dev validation for promotion/failure/rollback behavior:

```bash
python3 python/validate_gtfs_refresh.py
python3 python/validate_bootstrap_status.py
```
