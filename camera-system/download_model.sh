#!/bin/bash

# Download YOLOv8 HEF model for Hailo-8
# Run this on the Raspberry Pi

set -e

MODEL_DIR="models"
MODEL_FILE="yolov8s.hef"

echo "=========================================="
echo " YOLOv8 HEF Model Download"
echo "=========================================="
echo ""

# Create models directory
mkdir -p "$MODEL_DIR"

echo "Note: Pre-compiled HEF models require Hailo Model Zoo access."
echo "Options to get YOLOv8 HEF model:"
echo ""
echo "1. Download from Hailo Model Zoo (requires account)"
echo "   https://hailo.ai/developer-zone/model-zoo/"
echo ""
echo "2. Use Hailo Dataflow Compiler to convert ONNX to HEF"
echo "   - Download YOLOv8s ONNX from Ultralytics"
echo "   - Compile with Hailo DFC"
echo ""
echo "3. Use pre-trained model from Hailo examples"
echo "   Check: /usr/share/hailo-models/ (if available)"
echo ""

# Check if system has pre-installed models
if [ -d "/usr/share/hailo-models" ]; then
    echo "Checking system for pre-installed models..."
    find /usr/share/hailo-models -name "*.hef" -o -name "*yolo*"
    echo ""
fi

# Check for ONNX model and offer to download
echo "Would you like to download YOLOv8s ONNX model first? (y/n)"
read -r response

if [[ "$response" =~ ^[Yy]$ ]]; then
    echo ""
    echo "Downloading YOLOv8s ONNX model..."

    ONNX_URL="https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8s.onnx"
    ONNX_FILE="$MODEL_DIR/yolov8s.onnx"

    wget -O "$ONNX_FILE" "$ONNX_URL"

    if [ -f "$ONNX_FILE" ]; then
        echo "✅ Downloaded ONNX model to $ONNX_FILE"
        echo ""
        echo "Next steps:"
        echo "  1. Install Hailo Dataflow Compiler (DFC)"
        echo "  2. Convert ONNX to HEF:"
        echo "     hailo parser onnx $ONNX_FILE"
        echo "     hailo optimize yolov8s.har"
        echo "     hailo compiler yolov8s.har"
        echo ""
    else
        echo "❌ Download failed"
    fi
else
    echo ""
    echo "Please obtain YOLOv8s HEF model manually and place it at:"
    echo "  $MODEL_DIR/$MODEL_FILE"
    echo ""
fi

echo "=========================================="
echo " Model Setup Status"
echo "=========================================="

if [ -f "$MODEL_DIR/$MODEL_FILE" ]; then
    size=$(du -h "$MODEL_DIR/$MODEL_FILE" | cut -f1)
    echo "✅ HEF model found: $MODEL_FILE (size: $size)"
else
    echo "❌ HEF model not found: $MODEL_FILE"
    echo ""
    echo "The system will not work without a HEF model."
    echo "Please see options above to obtain one."
fi

echo ""
