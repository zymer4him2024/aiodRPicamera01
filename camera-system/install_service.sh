#!/bin/bash

# Install camera-detection as systemd service
# Run with: sudo ./install_service.sh

set -e

SERVICE_NAME="camera-detection"
SERVICE_FILE="$SERVICE_NAME.service"
SYSTEMD_DIR="/etc/systemd/system"

echo "=========================================="
echo " Installing Camera Detection Service"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root (use sudo)"
    exit 1
fi

# Check if service file exists
if [ ! -f "$SERVICE_FILE" ]; then
    echo "Error: Service file not found: $SERVICE_FILE"
    exit 1
fi

# Stop service if running
if systemctl is-active --quiet $SERVICE_NAME; then
    echo "Stopping existing service..."
    systemctl stop $SERVICE_NAME
fi

# Disable service if enabled
if systemctl is-enabled --quiet $SERVICE_NAME 2>/dev/null; then
    echo "Disabling existing service..."
    systemctl disable $SERVICE_NAME
fi

# Copy service file
echo "Installing service file..."
cp $SERVICE_FILE $SYSTEMD_DIR/
chmod 644 $SYSTEMD_DIR/$SERVICE_FILE

# Reload systemd
echo "Reloading systemd..."
systemctl daemon-reload

# Enable service
echo "Enabling service..."
systemctl enable $SERVICE_NAME

echo ""
echo "=========================================="
echo " Installation Complete"
echo "=========================================="
echo ""
echo "Service commands:"
echo "  Start:   sudo systemctl start $SERVICE_NAME"
echo "  Stop:    sudo systemctl stop $SERVICE_NAME"
echo "  Status:  sudo systemctl status $SERVICE_NAME"
echo "  Logs:    sudo journalctl -u $SERVICE_NAME -f"
echo "  Restart: sudo systemctl restart $SERVICE_NAME"
echo ""
echo "The service will auto-start on boot."
echo ""

# Ask if user wants to start now
read -p "Start service now? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Starting service..."
    systemctl start $SERVICE_NAME
    sleep 2
    systemctl status $SERVICE_NAME --no-pager
fi

echo ""
echo "Done!"
