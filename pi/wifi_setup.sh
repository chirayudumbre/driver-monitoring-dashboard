#!/bin/bash
# =============================================================================
#  wifi_setup.sh — Add/update phone hotspot credentials anytime
#  Usage: chmod +x wifi_setup.sh && ./wifi_setup.sh
# =============================================================================

echo ""
echo "=== WiFi Hotspot Setup ==="
echo ""
read -p "Phone Hotspot SSID (name): " SSID
read -s -p "Password:                  " PASS
echo ""

sudo bash -c "cat >> /etc/wpa_supplicant/wpa_supplicant.conf" << EOF

network={
    ssid="${SSID}"
    psk="${PASS}"
    priority=10
    key_mgmt=WPA-PSK
}
EOF

# Reload WiFi
sudo wpa_cli -i wlan0 reconfigure

echo ""
echo "Done! Connecting to '$SSID'..."
sleep 3

# Show connection status
if ping -c 1 8.8.8.8 &>/dev/null; then
    echo "Internet connected!"
else
    echo "Not connected yet — will connect on next reboot or when hotspot is in range."
fi
