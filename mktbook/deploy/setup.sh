#!/usr/bin/env bash
# ============================================================
# MktBook — Digital Ocean Droplet Setup Script
# Run this ONCE on a fresh Ubuntu 24.04 droplet as root:
#   bash setup.sh
#
# Droplet IP: 144.126.213.48
# ============================================================
set -euo pipefail

DROPLET_IP="144.126.213.48"
APP_DIR="/opt/mktbook"
APP_USER="mktbook"

echo "=== MktBook Droplet Setup ==="
echo "Droplet IP: $DROPLET_IP"
echo ""

# --------------------------------------------------
# 1. System packages
# --------------------------------------------------
echo "[1/7] Updating system and installing packages..."
apt-get update -qq
apt-get upgrade -y -qq
apt-get install -y -qq python3 python3-venv python3-pip nginx ufw git

# --------------------------------------------------
# 2. Firewall
# --------------------------------------------------
echo "[2/7] Configuring firewall (SSH + HTTP only)..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP (Nginx)
ufw --force enable

# --------------------------------------------------
# 3. Create application user
# --------------------------------------------------
echo "[3/7] Creating mktbook system user..."
if ! id "$APP_USER" &>/dev/null; then
    useradd --system --create-home --home-dir "$APP_DIR" --shell /bin/bash "$APP_USER"
else
    echo "  User $APP_USER already exists, skipping."
fi

# --------------------------------------------------
# 4. Create directory structure
# --------------------------------------------------
echo "[4/7] Setting up application directory..."
mkdir -p "$APP_DIR"
chown "$APP_USER:$APP_USER" "$APP_DIR"

# --------------------------------------------------
# 5. Python virtual environment
# --------------------------------------------------
echo "[5/7] Creating Python virtual environment..."
if [ ! -d "$APP_DIR/venv" ]; then
    sudo -u "$APP_USER" python3 -m venv "$APP_DIR/venv"
fi

# Install dependencies if requirements.txt exists
if [ -f "$APP_DIR/mktbook/requirements.txt" ]; then
    sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install --upgrade pip -q
    sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install -r "$APP_DIR/mktbook/requirements.txt" -q
    echo "  Dependencies installed."
else
    echo "  WARNING: requirements.txt not found. Run deploy/push.sh first, then re-run this script."
fi

# --------------------------------------------------
# 6. Nginx configuration
# --------------------------------------------------
echo "[6/7] Configuring Nginx reverse proxy..."
cp "$APP_DIR/mktbook/deploy/nginx-mktbook.conf" /etc/nginx/sites-available/mktbook
ln -sf /etc/nginx/sites-available/mktbook /etc/nginx/sites-enabled/mktbook
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx
systemctl enable nginx

# --------------------------------------------------
# 7. Systemd service
# --------------------------------------------------
echo "[7/7] Installing systemd service..."
cp "$APP_DIR/mktbook/deploy/mktbook.service" /etc/systemd/system/mktbook.service
systemctl daemon-reload
systemctl enable mktbook.service

# --------------------------------------------------
# .env check
# --------------------------------------------------
if [ ! -f "$APP_DIR/mktbook/.env" ]; then
    echo ""
    echo "============================================"
    echo "  IMPORTANT: .env file not found!"
    echo "  Copy .env.example and fill in your keys:"
    echo ""
    echo "    cp $APP_DIR/mktbook/.env.example $APP_DIR/mktbook/.env"
    echo "    nano $APP_DIR/mktbook/.env"
    echo ""
    echo "  Then start the service:"
    echo "    systemctl start mktbook"
    echo "============================================"
else
    echo ""
    echo "Starting MktBook service..."
    systemctl restart mktbook
    echo ""
    echo "============================================"
    echo "  MktBook is running!"
    echo "  Dashboard: http://$DROPLET_IP"
    echo ""
    echo "  Useful commands:"
    echo "    systemctl status mktbook     # Check status"
    echo "    journalctl -u mktbook -f     # View live logs"
    echo "    systemctl restart mktbook    # Restart"
    echo "    systemctl stop mktbook       # Stop"
    echo "============================================"
fi
