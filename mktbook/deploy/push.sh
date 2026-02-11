#!/usr/bin/env bash
# ============================================================
# MktBook — Push code to Digital Ocean droplet
# Run from your LOCAL machine (from the mktbook parent directory):
#   bash mktbook/deploy/push.sh
#
# Prerequisites: SSH access to the droplet as root
# ============================================================
set -euo pipefail

DROPLET_IP="144.126.213.48"
REMOTE_USER="root"
APP_DIR="/opt/mktbook"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Deploying MktBook to $DROPLET_IP ==="
echo "Source: $PROJECT_DIR"
echo ""

# --------------------------------------------------
# 1. Sync code to droplet (excludes .env, db files, __pycache__)
# --------------------------------------------------
echo "[1/3] Syncing code to droplet..."
rsync -avz --delete \
    --exclude '.env' \
    --exclude '*.db' \
    --exclude '*.db-shm' \
    --exclude '*.db-wal' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude 'venv/' \
    "$PROJECT_DIR/" \
    "$REMOTE_USER@$DROPLET_IP:$APP_DIR/mktbook/"

# --------------------------------------------------
# 2. Install/update dependencies
# --------------------------------------------------
echo "[2/3] Installing dependencies..."
ssh "$REMOTE_USER@$DROPLET_IP" "\
    $APP_DIR/venv/bin/pip install -r $APP_DIR/mktbook/requirements.txt -q"

# --------------------------------------------------
# 3. Restart the service
# --------------------------------------------------
echo "[3/3] Restarting MktBook service..."
ssh "$REMOTE_USER@$DROPLET_IP" "systemctl restart mktbook"

echo ""
echo "=== Deploy complete ==="
echo "Dashboard: http://$DROPLET_IP"
echo "Logs:      ssh $REMOTE_USER@$DROPLET_IP journalctl -u mktbook -f"
