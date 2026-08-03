#!/bin/bash

# Update and upgrade the system
echo "Updating system..."
sudo apt update && sudo apt upgrade -y

# Install required packages
echo "Installing necessary packages..."
sudo apt install -y python3 python3-pip git hostapd dnsmasq curl certbot python3-certbot

# Set up project directory
PROJECT_DIR="/home/subwaysign/project"
echo "Setting up project directory at $PROJECT_DIR..."
sudo mkdir -p $PROJECT_DIR

# Clone or pull the latest code
if [ ! -d "$PROJECT_DIR/.git" ]; then
    echo "Cloning project repository..."
    git clone https://github.com/thomascarlyonrussell/pi-subway-times.git $PROJECT_DIR
else
    echo "Repository already exists. Pulling latest changes..."
    cd $PROJECT_DIR && git pull origin main
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install --break-system-packages -r $PROJECT_DIR/requirements.txt

# === UPDATE AND CONFIGURE RGB MATRIX BONNET ===
echo "Installing and configuring Adafruit RGB Matrix Bonnet..."
cd $PROJECT_DIR
if [ ! -f "rgb-matrix.sh" ]; then
    curl -O https://raw.githubusercontent.com/adafruit/Raspberry-Pi-Installer-Scripts/main/rgb-matrix.sh
fi
sudo bash rgb-matrix.sh

# Setup logging
LOG_FILE="/var/log/subway_sign.log"
if [ ! -f "$LOG_FILE" ]; then
    echo "Creating log file..."
    sudo touch $LOG_FILE
    sudo chmod 666 $LOG_FILE
fi

sudo mkdir -p /var/lib/subway-sign/gtfs-static
sudo chown root:root /var/lib/subway-sign/gtfs-static
sudo chmod 755 /var/lib/subway-sign/gtfs-static

# Configure systemd service for subway sign display
echo "Setting up display service..."
cat <<EOF | sudo tee /etc/systemd/system/subway-sign.service
[Unit]
Description=Subway Time Sign Display
After=network-online.target gtfs-bootstrap.service
Wants=network-online.target
Requires=gtfs-bootstrap.service

[Service]
ExecStart=/usr/bin/python3 $PROJECT_DIR/python/main.py
WorkingDirectory=$PROJECT_DIR
Restart=always
User=root
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the service
sudo systemctl enable subway-sign

# Configure a conditional visual bootstrap before the live display takes the matrix.
echo "Setting up GTFS bootstrap service..."
cat <<EOF | sudo tee /etc/systemd/system/gtfs-bootstrap.service
[Unit]
Description=Bootstrap GTFS data and show setup progress when needed
After=network-online.target
Wants=network-online.target
Before=subway-sign.service

[Service]
Type=oneshot
WorkingDirectory=$PROJECT_DIR
ExecStart=/usr/bin/python3 $PROJECT_DIR/python/gtfs_bootstrap.py
User=root
Environment="PYTHONUNBUFFERED=1"
EOF

# Configure systemd service and timer for static GTFS refresh
echo "Setting up GTFS static refresh service and timer..."
cat <<EOF | sudo tee /etc/systemd/system/gtfs-static-refresh.service
[Unit]
Description=Refresh static MTA GTFS data
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
WorkingDirectory=$PROJECT_DIR
ExecStart=/usr/bin/python3 $PROJECT_DIR/python/gtfs_refresh.py
User=root
Environment="PYTHONUNBUFFERED=1"
EOF

cat <<EOF | sudo tee /etc/systemd/system/gtfs-static-refresh.timer
[Unit]
Description=Run GTFS static refresh on a semi-monthly cadence

[Timer]
OnCalendar=*-*-01,15 03:15:00
Persistent=true
Unit=gtfs-static-refresh.service

[Install]
WantedBy=timers.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable gtfs-static-refresh.timer
sudo systemctl start gtfs-static-refresh.timer

# Configure systemd service for web configuration UI
echo "Setting up web configuration service..."
cat <<EOF | sudo tee /etc/systemd/system/web-config.service
[Unit]
Description=Web Config for Subway Sign
After=network.target

[Service]
ExecStart=/usr/bin/python3 $PROJECT_DIR/python/web_config.py
WorkingDirectory=$PROJECT_DIR
Restart=always
User=subwaysign

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable web-config
sudo systemctl start web-config

# Setup Access Point mode (for first-time setup)
echo "Configuring WiFi Access Point mode..."
cat <<EOF | sudo tee /etc/hostapd/hostapd.conf
interface=wlan0
ssid=SubwaySign-Setup
hw_mode=g
channel=7
wpa=2
wpa_passphrase=SetupYourSign
EOF

# Unmask and enable hostapd service
sudo systemctl unmask hostapd
sudo systemctl enable hostapd
sudo systemctl enable dnsmasq

# # self-signed certificate for web config
# mkdir -p /home/subwaysign/certs
# cd /home/subwaysign/certs
# openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Block unused ports
sudo iptables -A INPUT -p tcp --dport 5000 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT
sudo iptables -A INPUT -j DROP


# Setup default configuration file
echo "Setting up default configuration..."
cat <<EOF | sudo tee /etc/matrix_config_default.json
{
    "wifi": {
        "ssid": "YOUR_WIFI_SSID",
        "password": "YOUR_WIFI_PASSWORD"
    },
    "display": {
        "brightness": 100,
        "mta_directions": "N",
        "refresh_time_delay": 30,
        "rotate_trip_delay": 4,
        "screen_refresh_interval": 2,
        "minimum_arrival_minutes": 2,
        "maximum_arrival_minutes": 99,
        "led_rows": 32,
        "led_columns": 64,
        "led_chain_length": 1,
        "led_parallel": 1,
        "led_hardware_mapping": "adafruit-hat",
        "line_direction_max_length": 10
    },
    "feed": {
        "mta_routes": "F,G",
        "mta_stop": "7 Av",
        "mta_feed_base_url": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2F"
    },
    "gtfs_static_refresh": {
        "enabled": true,
        "request_timeout_sec": 30,
        "transition_window_hours": 168,
        "snapshot_retention_count": 2,
        "service_action": "restart",
        "alert_command": "",
        "sources": [
            [
                "base",
                "https://rrgtfsfeeds.s3.amazonaws.com/gtfs_subway.zip"
            ],
            [
                "supplemented",
                "https://rrgtfsfeeds.s3.amazonaws.com/gtfs_supplemented.zip"
            ]
        ]
    }
}
EOF

# Copy the default settings as active settings (if no settings exist)
if [ ! -f "/etc/matrix_config.json" ]; then
    sudo cp /etc/matrix_config_default.json /etc/matrix_config.json
fi
sudo chown subwaysign:subwaysign /etc/matrix_config_default.json /etc/matrix_config.json
sudo chmod 664 /etc/matrix_config_default.json /etc/matrix_config.json

# Starting subway-sign runs the visual bootstrap first when no valid snapshot exists.
sudo systemctl start subway-sign


# Request user confirmation to reboot
read -p "Setup complete. Do you want to reboot now? (y/n): " confirm
if [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]]; then
    echo "Rebooting now..."
    sudo reboot
else
    echo "Reboot canceled. Please reboot manually to apply changes."
fi
