#!/bin/bash
# =============================================================================
#  setup_pi.sh  —  Run once on Raspberry Pi 4 to set up the project
#  Usage:  chmod +x setup_pi.sh && ./setup_pi.sh
# =============================================================================

set -e  # exit on first error

echo ""
echo "=================================================="
echo "  AI Driver Monitoring — Raspberry Pi 4 Setup"
echo "=================================================="
echo ""

# ── 1. System packages ────────────────────────────────────────────────────────
echo "[1/6] Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y \
    python3-pip python3-venv python3-dev \
    libopencv-dev libatlas-base-dev \
    libjpeg-dev libpng-dev \
    git wget curl \
    libgpio2 python3-rpi.gpio \
    --no-install-recommends
echo "      System packages installed."

# ── 2. Virtual environment ────────────────────────────────────────────────────
echo "[2/6] Creating Python virtual environment..."
cd /home/pi/DriverProject
python3 -m venv .venv --system-site-packages
source .venv/bin/activate
pip install --upgrade pip --quiet
echo "      Virtual environment ready."

# ── 3. Python packages ────────────────────────────────────────────────────────
echo "[3/6] Installing Python packages (this takes ~5 min on Pi 4)..."
pip install --quiet \
    opencv-python-headless \
    mediapipe \
    "ultralytics>=8.0" \
    requests \
    python-dotenv \
    RPi.GPIO
echo "      Python packages installed."

# ── 4. .env file check ────────────────────────────────────────────────────────
echo "[4/6] Checking .env configuration..."
if [ ! -f ".env" ]; then
    echo "      WARNING: .env not found! Creating template..."
    cat > .env << 'EOF'
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key-here
VEHICLE_ID=MH12AB1234
EOF
    echo "      Edit .env with your Supabase credentials before running!"
else
    echo "      .env found."
fi

# ── 5. WiFi hotspot auto-connect ──────────────────────────────────────────────
echo "[5/6] Configuring WiFi auto-connect..."
echo ""
echo "  Enter your phone hotspot details:"
read -p "  Hotspot SSID (WiFi name): " HOTSPOT_SSID
read -s -p "  Hotspot Password:         " HOTSPOT_PASS
echo ""

# Write wpa_supplicant config
sudo bash -c "cat >> /etc/wpa_supplicant/wpa_supplicant.conf" << EOF

network={
    ssid="${HOTSPOT_SSID}"
    psk="${HOTSPOT_PASS}"
    priority=10
    key_mgmt=WPA-PSK
}
EOF

echo "      WiFi hotspot configured. Pi will auto-connect on boot."

# ── 6. Systemd service (auto-start on boot) ───────────────────────────────────
echo "[6/6] Installing systemd auto-start service..."

sudo bash -c 'cat > /etc/systemd/system/driver-monitor.service' << 'EOF'
[Unit]
Description=AI Driver Monitoring System
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/DriverProject
ExecStart=/home/pi/DriverProject/.venv/bin/python3 pi/main_pi.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable driver-monitor.service
echo "      Service installed and enabled."

echo ""
echo "=================================================="
echo "  Setup Complete!"
echo "=================================================="
echo ""
echo "  Next steps:"
echo "  1. Edit .env with your Supabase URL and KEY"
echo "  2. Reboot the Pi:  sudo reboot"
echo "  3. Monitor logs:   sudo journalctl -u driver-monitor -f"
echo "  4. Stop service:   sudo systemctl stop driver-monitor"
echo ""
