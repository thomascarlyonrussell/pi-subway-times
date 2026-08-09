#!/bin/bash

# Parse command line flags
SKIP_MATRIX=false
FORCE_MATRIX=false
NON_INTERACTIVE=false

for arg in "$@"; do
    case $arg in
        --skip-matrix|--no-matrix)
            SKIP_MATRIX=true
            ;;
        --force-matrix)
            FORCE_MATRIX=true
            ;;
        --non-interactive|-y|--yes)
            NON_INTERACTIVE=true
            ;;
    esac
done

# Update and upgrade the system
echo "Updating system..."
sudo apt update && sudo apt upgrade -y

# Install required packages
echo "Installing necessary packages..."
sudo apt install -y python3 python3-pip python3-venv git hostapd dnsmasq curl certbot python3-certbot

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

# Install Python dependencies using uv
echo "Installing Python dependencies with uv..."
if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi
cd "$PROJECT_DIR"
uv sync

# === UPDATE AND CONFIGURE RGB MATRIX BONNET ===
if [ "$FORCE_MATRIX" = false ] && { [ "$SKIP_MATRIX" = true ] || python3 -c "import rgbmatrix" &>/dev/null || [ -d "$PROJECT_DIR/.rgb-matrix-installer-env" ]; }; then
    echo "RGB Matrix driver/installer environment already exists. Skipping Adafruit matrix setup."
    echo "  (Pass --force-matrix if you need to re-run Adafruit's installer)."
else
    echo "Installing and configuring Adafruit RGB Matrix Bonnet..."
    cd "$PROJECT_DIR"
    if [ ! -f "rgb-matrix.py" ]; then
        curl -fLO https://raw.githubusercontent.com/adafruit/Raspberry-Pi-Installer-Scripts/main/rgb-matrix.py
    fi
    python3 -m venv --system-site-packages "$PROJECT_DIR/.rgb-matrix-installer-env"
    source "$PROJECT_DIR/.rgb-matrix-installer-env/bin/activate"
    pip install --upgrade setuptools adafruit-python-shell click
    sudo -E env PATH="$PATH" python3 rgb-matrix.py
    deactivate
    cd "$PROJECT_DIR"
fi

# The soldered GPIO4-to-GPIO18 bridge enables the Bonnet's quality mode.
# It conflicts with onboard audio, so maintain the same blacklist that the
# Adafruit installer writes when its Quality option is selected.
echo "Disabling onboard audio for RGB Matrix Bonnet quality mode..."
echo "blacklist snd_bcm2835" | sudo tee /etc/modprobe.d/blacklist-rgb-matrix.conf > /dev/null

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

# Configure systemd service for opening boot splash screen
echo "Setting up boot splash service..."
cat <<EOF | sudo tee /etc/systemd/system/subway-splash.service
[Unit]
Description=Subway Sign Opening Boot Splash Screen
DefaultDependencies=no
After=local-fs.target
Before=gtfs-bootstrap.service subway-sign.service network-online.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/.venv/bin/subway-splash
Restart=no
User=root
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=sysinit.target multi-user.target
EOF

sudo systemctl enable subway-splash

# Configure systemd service for subway sign display
echo "Setting up display service..."
cat <<EOF | sudo tee /etc/systemd/system/subway-sign.service
[Unit]
Description=Subway Time Sign Display
After=network-online.target subway-splash.service gtfs-bootstrap.service
Wants=network-online.target
Requires=gtfs-bootstrap.service

[Service]
ExecStartPre=/usr/bin/systemctl stop subway-splash.service
ExecStart=$PROJECT_DIR/.venv/bin/subway-display
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
After=network-online.target subway-splash.service
Wants=network-online.target
Before=subway-sign.service

[Service]
Type=oneshot
WorkingDirectory=$PROJECT_DIR
ExecStartPre=/usr/bin/systemctl stop subway-splash.service
ExecStart=$PROJECT_DIR/.venv/bin/subway-gtfs-bootstrap
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
ExecStart=$PROJECT_DIR/.venv/bin/subway-gtfs-refresh
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
ExecStart=$PROJECT_DIR/.venv/bin/subway-web-config
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


# Install the package-owned default template and preserve configured devices.
echo "Installing default configuration template..."
sudo install -o root -g root -m 644 "$PROJECT_DIR/setup/matrix_config_default.json" /etc/matrix_config_default.json

# Copy the default settings as active settings only for an unconfigured device.
if [ ! -f "/etc/matrix_config.json" ]; then
    sudo cp /etc/matrix_config_default.json /etc/matrix_config.json
fi
sudo chown root:subwaysign /etc/matrix_config.json
sudo chmod 664 /etc/matrix_config.json

# Starting subway-sign runs the visual bootstrap first when no valid snapshot exists.
sudo systemctl start subway-sign


# Request user confirmation to reboot (skips prompt if non-interactive)
if [ "$NON_INTERACTIVE" = true ] || [ ! -t 0 ]; then
    echo "Setup complete. Non-interactive run finished."
else
    read -p "Setup complete. Do you want to reboot now? (y/n): " confirm
    if [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]]; then
        echo "Rebooting now..."
        sudo reboot
    else
        echo "Reboot canceled. Please reboot manually to apply changes."
    fi
fi
