#!/bin/bash

# Search for HEF model files on the system
# Run this on Raspberry Pi to find existing Hailo models

echo "=========================================="
echo " Searching for HEF Models"
echo "=========================================="
echo ""

echo "This may take a few minutes..."
echo ""

# Search common locations first
echo "1. Checking common Hailo directories..."
echo "   /usr/share/hailo-models/"
if [ -d "/usr/share/hailo-models" ]; then
    find /usr/share/hailo-models -name "*.hef" 2>/dev/null
else
    echo "   Directory not found"
fi

echo ""
echo "   /opt/hailo/"
if [ -d "/opt/hailo" ]; then
    find /opt/hailo -name "*.hef" 2>/dev/null
else
    echo "   Directory not found"
fi

echo ""
echo "   /usr/local/share/"
find /usr/local/share -name "*.hef" 2>/dev/null

echo ""
echo "   Home directory (~)"
find ~ -name "*.hef" 2>/dev/null

# Broader search
echo ""
echo "2. Searching entire system (this takes longer)..."
echo "   /usr/"
sudo find /usr -name "*.hef" 2>/dev/null

echo ""
echo "   /opt/"
sudo find /opt -name "*.hef" 2>/dev/null

echo ""
echo "3. Searching for YOLO-related files..."
sudo find /usr -iname "*yolo*.hef" 2>/dev/null
sudo find /opt -iname "*yolo*.hef" 2>/dev/null
find ~ -iname "*yolo*.hef" 2>/dev/null

echo ""
echo "4. Checking for Hailo example/demo directories..."
sudo find /usr -type d -iname "*hailo*" -o -type d -iname "*example*" -o -type d -iname "*demo*" 2>/dev/null | grep -i hailo

echo ""
echo "=========================================="
echo " Search Complete"
echo "=========================================="
echo ""

# Check if any HEF found
HEF_COUNT=$(sudo find / -name "*.hef" 2>/dev/null | wc -l)

if [ "$HEF_COUNT" -gt 0 ]; then
    echo "✅ Found $HEF_COUNT HEF file(s)"
    echo ""
    echo "All HEF files found:"
    sudo find / -name "*.hef" -exec ls -lh {} \; 2>/dev/null
    echo ""
    echo "To use one of these models, copy it:"
    echo "  sudo cp /path/to/model.hef ~/camera-system/models/yolov8n.hef"
    echo "  sudo chown $USER:$USER ~/camera-system/models/yolov8n.hef"
else
    echo "❌ No HEF files found on system"
    echo ""
    echo "Options:"
    echo "  1. Download from Hailo Model Zoo (requires account)"
    echo "  2. Compile ONNX to HEF using Hailo Dataflow Compiler"
    echo "  3. Check if Hailo SDK includes example models"
    echo ""
    echo "Run this to check Hailo package contents:"
    echo "  dpkg -L hailort 2>/dev/null | grep -E '\.hef|model|example'"
fi

echo ""
