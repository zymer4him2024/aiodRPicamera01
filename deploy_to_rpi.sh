#!/bin/bash

# Auto-deployment script - Syncs camera-system to Raspberry Pi
# This script builds, packages, and deploys to RPi automatically

set -e

# Configuration
RPI_USER="digioptics_od"
RPI_HOST="192.168.0.11"
RPI_PATH="/home/digioptics_od"
LOCAL_PATH="/Users/shawnshlee/1_Claude Code/AI OD RPiv01/camera-system"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "=========================================="
echo " Camera System - Auto Deploy to RPi"
echo "=========================================="
echo ""

# Check if local path exists
if [ ! -d "$LOCAL_PATH" ]; then
    echo -e "${RED}Error: Local path not found: $LOCAL_PATH${NC}"
    exit 1
fi

# Test RPi connection
echo "Testing connection to RPi..."
if ! ssh -o ConnectTimeout=5 $RPI_USER@$RPI_HOST "echo 'Connected'" > /dev/null 2>&1; then
    echo -e "${RED}Error: Cannot connect to RPi at $RPI_USER@$RPI_HOST${NC}"
    echo "Please check:"
    echo "  1. RPi is powered on and connected to network"
    echo "  2. SSH is enabled on RPi"
    echo "  3. IP address is correct (currently: $RPI_HOST)"
    echo "  4. SSH keys are set up or password is available"
    exit 1
fi
echo -e "${GREEN}✓ Connected to RPi${NC}"
echo ""

# Create backup on RPi
echo "Creating backup on RPi..."
ssh $RPI_USER@$RPI_HOST "
    if [ -d $RPI_PATH/camera-system ]; then
        timestamp=\$(date +%Y%m%d_%H%M%S)
        if [ -d $RPI_PATH/camera-system-backup ]; then
            rm -rf $RPI_PATH/camera-system-backup
        fi
        cp -r $RPI_PATH/camera-system $RPI_PATH/camera-system-backup-\$timestamp
        echo 'Backup created: camera-system-backup-'\$timestamp
    fi
" || echo -e "${YELLOW}No existing installation to backup${NC}"
echo ""

# Stop running service if exists
echo "Stopping service if running..."
ssh $RPI_USER@$RPI_HOST "
    if systemctl is-active --quiet camera-detection; then
        sudo systemctl stop camera-detection
        echo 'Service stopped'
    else
        echo 'Service not running'
    fi
" 2>/dev/null || echo "No service installed"
echo ""

# Sync files to RPi
echo "Syncing files to RPi..."
rsync -avz --progress \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='.DS_Store' \
    --exclude='*.log' \
    --exclude='logs/*' \
    --exclude='venv' \
    --exclude='.git' \
    --exclude='models/*.onnx' \
    "$LOCAL_PATH/" "$RPI_USER@$RPI_HOST:$RPI_PATH/camera-system/"

echo -e "${GREEN}✓ Files synced${NC}"
echo ""

# Make scripts executable
echo "Setting permissions..."
ssh $RPI_USER@$RPI_HOST "
    cd $RPI_PATH/camera-system
    chmod +x *.sh
    chmod +x *.py
    chmod +x test_*.py
    chmod +x agents/*.py
"
echo -e "${GREEN}✓ Permissions set${NC}"
echo ""

# Check/create virtual environment
echo "Checking Python environment..."
ssh $RPI_USER@$RPI_HOST "
    cd $RPI_PATH/camera-system

    if [ ! -d venv ]; then
        echo 'Creating virtual environment...'
        python3 -m venv venv
    fi

    source venv/bin/activate

    echo 'Installing/updating dependencies...'
    pip install --upgrade pip > /dev/null
    pip install -r requirements.txt

    echo '✓ Python environment ready'
"
echo ""

# Check Hailo installation
echo "Checking Hailo installation..."
ssh $RPI_USER@$RPI_HOST "
    if lsusb | grep -q Hailo; then
        echo '✓ Hailo device detected'
    else
        echo '⚠️  Hailo device not found (this is OK if testing without Hailo)'
    fi

    if python3 -c 'import hailort' 2>/dev/null; then
        echo '✓ Hailo Python package installed'
    else
        echo '⚠️  Hailo Python package not installed'
        echo '   Install with: pip3 install hailort'
    fi
" || true
echo ""

# Check camera
echo "Checking camera..."
ssh $RPI_USER@$RPI_HOST "
    if ls /dev/video* > /dev/null 2>&1; then
        echo '✓ Camera device(s) found:'
        ls -la /dev/video*
    else
        echo '⚠️  No camera devices found'
    fi
" || echo "No camera detected"
echo ""

# Check HEF model
echo "Checking model file..."
ssh $RPI_USER@$RPI_HOST "
    if [ -f $RPI_PATH/camera-system/models/yolov8s.hef ]; then
        size=\$(du -h $RPI_PATH/camera-system/models/yolov8s.hef | cut -f1)
        echo '✓ HEF model found (size: '\$size')'
    else
        echo '⚠️  HEF model not found at models/yolov8s.hef'
        echo '   Download or compile YOLOv8 model and place it there'
    fi
" || echo "Model check skipped"
echo ""

# Offer to run tests
echo "=========================================="
echo " Deployment Complete"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. SSH to RPi: ssh $RPI_USER@$RPI_HOST"
echo "  2. Test system: cd camera-system && ./run_tests.sh"
echo "  3. Run manually: source venv/bin/activate && python3 main.py"
echo "  4. Or install service: sudo ./install_service.sh"
echo ""

# Ask if user wants to run tests remotely
read -p "Run tests on RPi now? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Running tests on RPi..."
    echo "=========================================="
    ssh -t $RPI_USER@$RPI_HOST "
        cd $RPI_PATH/camera-system
        source venv/bin/activate
        ./run_tests.sh
    "
fi

echo ""
echo -e "${GREEN}Deployment finished!${NC}"
