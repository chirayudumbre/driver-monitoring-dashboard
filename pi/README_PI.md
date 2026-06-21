# Raspberry Pi 4 — AI Driver Monitoring System

## Hardware Required

| Component | Spec |
|---|---|
| Raspberry Pi 4 | 2GB RAM minimum (4GB recommended) |
| SD Card | 64GB (yours ✅) |
| USB Camera | Any USB webcam, or Pi CSI camera |
| Active Buzzer | 3.3V–5V active buzzer |
| Car Power | 12V → USB-C 5V/3A adapter (must be 3A for Pi 4) |
| Jumper Wires | 2x female-to-female |

---

## Buzzer Wiring

```
Raspberry Pi 4 GPIO Header
─────────────────────────────────
Pin 11  (GPIO 17) ──── Buzzer + (red wire)
Pin  9  (GND)     ──── Buzzer - (black wire)
─────────────────────────────────
```

GPIO pin map:
```
     3V3  [1] [2]  5V
   GPIO2  [3] [4]  5V
   GPIO3  [5] [6]  GND ◄─── Buzzer (-)
   GPIO4  [7] [8]  GPIO14
     GND  [9] [10] GPIO15
 GPIO17 [11] [12] GPIO18  ◄─── Buzzer (+)  Pin 11
```

---

## Camera Connection

**Option A — USB Camera (easier):**
- Plug USB camera into any USB port on Pi 4
- Camera index = 0 in `main_pi.py`

**Option B — CSI Ribbon Camera:**
- Connect to CSI port on Pi 4
- Run: `sudo raspi-config` → Interface Options → Camera → Enable
- Change `CAMERA_INDEX = 0` to use `/dev/video0`

---

## Car Power Wiring

```
Car 12V Battery / Cigarette Lighter
          ↓
  USB Car Charger (12V → 5V, must be ≥3A)
          ↓
    USB-C Cable
          ↓
  Raspberry Pi 4 (USB-C port)
```

**Important:** Pi 4 needs 5V/3A. Cheap 1A or 2A chargers will cause undervoltage 
and random crashes. Use a quality 3A USB-C car charger.

---

## SD Card Setup (First Time)

1. Flash **Raspberry Pi OS Lite (64-bit)** using Raspberry Pi Imager
2. In Imager settings before flashing:
   - Enable SSH
   - Set username: `pi`
   - Set password: (your choice)
   - Set WiFi: your home WiFi (to do initial setup)
3. Flash to 64GB SD card and insert into Pi

---

## Installation (Run Once)

SSH into your Pi or connect keyboard/monitor:

```bash
# Clone or copy the project to Pi
git clone <your-repo> /home/pi/DriverProject
# OR copy files via FileZilla/SCP

# Run setup script
cd /home/pi/DriverProject/pi
chmod +x setup_pi.sh
./setup_pi.sh
```

The setup script will:
- Install all system and Python packages
- Ask for your phone hotspot name + password
- Create systemd service (auto-start on boot)
- Configure WiFi auto-connect

---

## Configure Supabase (.env)

```bash
nano /home/pi/DriverProject/.env
```

```
SUPABASE_URL=https://pynlvofyngrluozqqlrv.supabase.co
SUPABASE_KEY=your-anon-key
VEHICLE_ID=MH12AB1234
```

Save: `Ctrl+X` → `Y` → `Enter`

---

## Phone Hotspot Setup

On your Android/iPhone:
1. Settings → Personal Hotspot → Turn ON
2. Note the hotspot name and password

On the Pi (run once):
```bash
cd /home/pi/DriverProject/pi
./wifi_setup.sh
```

The Pi will automatically connect to your phone hotspot whenever it's available.

---

## Running

**Manual run (testing):**
```bash
cd /home/pi/DriverProject
.venv/bin/python3 pi/main_pi.py
```

**Auto-run on boot (production):**
```bash
sudo systemctl start driver-monitor    # start now
sudo systemctl enable driver-monitor   # enable on every boot
```

---

## Monitoring Logs

```bash
# Live logs
sudo journalctl -u driver-monitor -f

# Last 100 lines
sudo journalctl -u driver-monitor -n 100

# Check service status
sudo systemctl status driver-monitor
```

---

## How It Works in the Car

```
Car starts
    ↓
Pi 4 powers on (from car USB charger)
    ↓ (30-45 sec boot time)
driver-monitor.service starts automatically
    ↓
Camera opens, models load (~15 sec)
    ↓
2 short beeps = system ready ✅
    ↓
Monitoring begins (headless, no screen needed)
    ↓
Alert detected?
    ├── Buzzer fires (GPIO 17)
    ├── Snapshot saved to SD card
    ├── Internet available? → Send to Supabase instantly
    └── No internet?       → Save to offline queue (SQLite)
                                    ↓
                           Internet returns → auto-sync all queued alerts
    ↓
Car turns off → Pi shuts down (or add a safe shutdown button)
```

---

## Offline Queue

All alerts are stored in:
```
/home/pi/DriverProject/data/offline_queue.db
```

When internet is available (phone hotspot ON), the background thread
syncs pending alerts every 30 seconds automatically.

Check queue status in live logs:
```
[SYNC] Synced 5 alert(s) to Supabase (0 remaining)
[SYNC] No internet — 3 alert(s) queued on SD card
```

---

## Dashboard Access

After alerts are synced to Supabase, open the dashboard from any device:
- Your laptop: run `streamlit run dashboard/dashboard.py`
- Streamlit Cloud: deploy `app.py`
- Login with your vehicle ID and password

---

## Beep Codes

| Pattern | Meaning |
|---|---|
| 2 short beeps | System started successfully |
| 3 beeps (0.3s each) | Drowsiness detected |
| 2 beeps (0.2s each) | Distraction detected |
| 4 rapid beeps | Mobile phone detected |
| 1 long beep | System shutting down |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Pi won't start | Check 5V/3A USB-C car charger |
| Camera not found | `ls /dev/video*` — check camera index |
| No Supabase sync | Check hotspot is ON, verify .env credentials |
| Buzzer not working | Check GPIO 17 wiring, verify active buzzer |
| Service not starting | `sudo journalctl -u driver-monitor -n 50` |
| Models not found | Check `models/` folder has `.task` and `.pt` files |
