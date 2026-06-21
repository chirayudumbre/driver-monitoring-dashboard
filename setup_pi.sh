#!/bin/bash
# ─────────────────────────────────────────────────────────────
# Raspberry Pi Setup Script — AI Driver Monitoring System
# Run once on your Pi: bash setup_pi.sh
# ─────────────────────────────────────────────────────────────

echo "=== AI Driver Monitor — Pi Setup ==="

# 1. Update system
sudo apt-get update && sudo apt-get upgrade -y

# 2. Install system dependencies
sudo apt-get install -y \
    python3-pip \
    python3-venv \
    python3-opencv \
    libatlas-base-dev \
    libjasper-dev \
    libqtgui4 \
    libqt4-test \
    libhdf5-dev \
    libhdf5-serial-dev \
    libilmbase-dev \
    libopenexr-dev \
    libgstreamer1.0-dev \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libcamera-apps \
    v4l-utils

# 3. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 4. Upgrade pip
pip install --upgrade pip setuptools wheel

# 5. Install Python packages
pip install -r requirements_pi.txt

# 6. Optional: Install YOLO nano (only for Pi 4 with 4GB+ RAM)
# pip install ultralytics==8.1.0

# 7. Create .env file if not exists
if [ ! -f .env ]; then
    echo "SUPABASE_URL=https://your-project.supabase.co" > .env
    echo "SUPABASE_KEY=your-anon-key" >> .env
    echo ">>> Edit .env with your Supabase credentials!"
fi

# 8. Create required directories
mkdir -p data/snapshots
mkdir -p models

echo ""
echo "=== Setup complete! ==="
echo ""
echo "Next steps:"
echo "  1. Edit .env with your Supabase credentials"
echo "  2. Copy models/yolov8n.pt if using phone detection"
echo "  3. Run: source .venv/bin/activate && python mainpi.py"
