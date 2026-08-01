#!/bin/bash
# Android 12 Web Emulator - Setup Script
# Run this inside GitHub Codespaces or a Linux server
set -e

echo "========================================"
echo "  Android 12 Web Emulator - Setup"
echo "========================================"

# Check if running in Codespaces
if [ -n "$CODESPACE_NAME" ]; then
    echo "[INFO] Running in GitHub Codespaces: $CODESPACE_NAME"
    # Codespaces already has Docker
    echo "[INFO] Checking Docker..."
    if ! docker info >/dev/null 2>&1; then
        echo "[ERROR] Docker is not running. Please ensure Docker is available."
        exit 1
    fi
else
    echo "[INFO] Running on standalone server"
    # Install Docker if not present
    if ! command -v docker &>/dev/null; then
        echo "[INFO] Installing Docker..."
        curl -fsSL https://get.docker.com | sh
        systemctl start docker
        systemctl enable docker
    fi
fi

# Pull Redroid (Android 12 container)
echo "[INFO] Pulling Redroid Android 12 image..."
docker pull redroid/redroid:android-tools-latest 2>/dev/null || docker pull redroid/redroid:12.0.0-latest 2>/dev/null || {
    echo "[WARN] Could not pull Redroid image. Will try at start time."
}

# Install websockify for VNC->WebSocket bridging
echo "[INFO] Installing websockify..."
pip install websockify -q 2>/dev/null || pip3 install websockify -q 2>/dev/null || {
    echo "[INFO] Installing pip first..."
    apt-get update -qq && apt-get install -y -qq python3-pip
    pip3 install websockify -q
}

# Install Android platform tools (adb)
echo "[INFO] Installing Android platform-tools..."
if ! command -v adb &>/dev/null; then
    PLATFORM_TOOLS_URL="https://dl.google.com/android/repository/platform-tools-latest-linux.zip"
    wget -q "$PLATFORM_TOOLS_URL" -O /tmp/platform-tools.zip
    unzip -q /tmp/platform-tools.zip -d /opt/
    ln -sf /opt/platform-tools/adb /usr/local/bin/adb
    rm /tmp/platform-tools.zip
fi

echo "[OK] adb version: $(adb version 2>/dev/null | head -1)"

# Install noVNC web client
echo "[INFO] Installing noVNC..."
if [ ! -d /opt/novnc ]; then
    git clone --depth 1 https://github.com/novnc/noVNC.git /opt/novnc 2>/dev/null || {
        wget -q https://github.com/novnc/noVNC/archive/refs/tags/v1.4.0.tar.gz -O /tmp/novnc.tar.gz
        mkdir -p /opt/novnc
        tar xzf /tmp/novnc.tar.gz -C /opt/novnc --strip-components=1
        rm /tmp/novnc.tar.gz
    }
fi

echo ""
echo "========================================"
echo "  Setup Complete!"
echo "========================================"
echo ""
echo "Next step: Run ./start.sh to start the emulator"
echo ""
