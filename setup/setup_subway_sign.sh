#!/bin/bash

# Update and upgrade the system
echo "Updating system..."
sudo apt update && sudo apt upgrade -y

# Install required packages
echo "Installing necessary packages..."
sudo apt install -y python3 python3-pip python3-flask git hostapd dnsmasq \
  python3-rpi.gpio python3-requests curl

# Set up project directory
PROJECT_DIR="/home/pi/subway_sign"
echo "Setting up project directory at $PROJECT_DIR..."
mkdir -p $PROJECT_DIR

# Clone or pull the latest code
if [ ! -d "$PROJECT_DIR/.git" ]; then
    echo "Cloning project repository..."
    git clone https://github.com/tomrussell-willdan/pi-subway-times.git $PROJECT_DIR
else
    echo "Repository already exists. Pulling latest changes..."
    cd $PROJECT_DIR && git pull origin main
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install -r $PROJECT_DIR/requirements.txt

# Setup logging
LOG_FILE="/var/log/subway_sign.log"
if [ ! -f "$LOG_FILE" ]; then
    echo "Creating log file..."
    sudo touch $LOG_FILE
    sudo chmod 666 $LOG_FILE
fi

# Configure systemd service for subway sign display
echo "Setting up display service..."
cat <<EOF | sudo tee /etc/systemd/system/subway-sign.service
[Unit]
Description=Subway Time Sign Display
After=network.target

[Service]
ExecStart=/usr/bin/python3 $PROJECT_DIR/subway_sign.py
WorkingDirectory=$PROJECT_DIR
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the service
sudo systemctl enable subway-sign
sudo systemctl start subway-sign

# Configure systemd service for reset button
echo "Setting up reset button service..."
cat <<EOF | sudo tee /etc/systemd/system/reset-button.service
[Unit]
Description=Physical Reset Button
After=multi-user.target

[Service]
ExecStart=/usr/bin/python3 $PROJECT_DIR/reset_button.py
WorkingDirectory=$PROJECT_DIR
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable reset-button
sudo systemctl start reset-button

# Configure systemd service for web configuration UI
echo "Setting up web configuration service..."
cat <<EOF | sudo tee /etc/systemd/system/web-config.service
[Unit]
Description=Web Config for Subway Sign
After=network.target

[Service]
ExecStart=/usr/bin/python3 $PROJECT_DIR/web_config.py
WorkingDirectory=$PROJECT_DIR
Restart=always
User=pi

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
auth_algs=1
wpa=2
wpa_passphrase=SetupYourSign
EOF

sudo systemctl enable hostapd
sudo systemctl enable dnsmasq

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
    }
}
EOF

# Copy the default settings as active settings (if no settings exist)
if [ ! -f "/etc/matrix_config.json" ]; then
    sudo cp /etc/matrix_config_default.json /etc/matrix_config.json
fi

# === UPDATE AND CONFIGURE RGB MATRIX BONNET ===
echo "Installing and configuring Adafruit RGB Matrix Bonnet..."
cd $PROJECT_DIR
curl -O https://raw.githubusercontent.com/adafruit/Raspberry-Pi-Installer-Scripts/main/rgb-matrix.sh
sudo bash rgb-matrix.sh

# Reboot to apply changes
echo "Setup complete. Rebooting now..."
sudo reboot
