# Hailo-8 HAT+ Setup and Testing Guide

Complete guide for getting camera inference working with Hailo-8 HAT+ on Raspberry Pi.

---

## Prerequisites

### Hardware
- ✅ Raspberry Pi 4/5 (4GB+ RAM recommended)
- ✅ Hailo-8 HAT+ (AI accelerator)
- ✅ USB camera or CSI camera
- ✅ MicroSD card (32GB+ recommended)
- ✅ Power supply (official RPi power adapter recommended)

### Software
- Raspberry Pi OS (64-bit, Bookworm or later)
- Python 3.9+
- Internet connection for initial setup

---

## Step 1: Install Hailo Software

### 1.1 Install Hailo Runtime (HailoRT)

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3-pip python3-dev git cmake build-essential

# Install HailoRT
wget https://hailo.ai/wp-content/uploads/2024/01/hailort_4.16.0_arm64.deb
sudo dpkg -i hailort_4.16.0_arm64.deb
sudo apt --fix-broken install -y
```

### 1.2 Install Hailo Python Package

```bash
pip3 install hailort
```

### 1.3 Verify Hailo Installation

```bash
# Check Hailo device
lsusb | grep Hailo

# Expected output:
# Bus 001 Device 002: ID 2b40:XXXX Hailo Technologies Ltd.

# Check device files
ls -la /dev/hailo*

# Expected output:
# /dev/hailo0
```

---

## Step 2: Prepare YOLOv8 Model for Hailo

### 2.1 Option A: Use Pre-compiled HEF (Recommended)

Download pre-compiled YOLOv8s model from Hailo Model Zoo:

```bash
# Create models directory
mkdir -p /home/digioptics_od/camera-system/models

# Download YOLOv8s HEF (example - check Hailo Model Zoo for latest)
cd /home/digioptics_od/camera-system/models
wget https://hailo-model-zoo.s3.amazonaws.com/ModelZoo/Compiled/v2.10.0/yolov8s.hef
```

### 2.2 Option B: Compile Your Own Model

If you need to compile a custom model:

1. **Install Hailo Dataflow Compiler** (requires separate license)

2. **Convert ONNX to HEF:**
   ```bash
   hailo parser onnx yolov8s.onnx
   hailo optimize yolov8s.har
   hailo compiler yolov8s.har --output yolov8s.hef
   ```

3. **Transfer to RPi:**
   ```bash
   scp yolov8s.hef digioptics_od@192.168.0.11:/home/digioptics_od/camera-system/models/
   ```

### 2.3 Verify Model File

```bash
cd /home/digioptics_od/camera-system/models
ls -lh yolov8s.hef

# Should show file size (typically 15-25 MB for YOLOv8s)
```

---

## Step 3: Configure Camera System

### 3.1 Update Detection Config

Edit `/home/digioptics_od/camera-system/config/detection_config.json`:

```json
{
  "model_path": "/home/digioptics_od/camera-system/models/yolov8s.hef",
  "confidence_threshold": 0.5,
  "nms_threshold": 0.45,
  "classes": ["person", "car", "bus", "truck", "motorcycle"],
  "input_size": [640, 640],
  "device": "hailo"
}
```

### 3.2 Verify Camera Config

Edit `/home/digioptics_od/camera-system/config/camera_config.json`:

```json
{
  "device_id": 0,
  "resolution": [1920, 1080],
  "fps": 30,
  "format": "MJPEG",
  "flip_horizontal": false,
  "flip_vertical": false
}
```

Find your camera device:
```bash
ls -la /dev/video*
```

Update `device_id` if needed (0, 1, 2, etc.)

### 3.3 Configure Firebase Backend (Optional)

Edit `/home/digioptics_od/camera-system/config/backend_config.json`:

```json
{
  "camera_id": "your_camera_id",
  "site_id": "your_site_id",
  "endpoints": {
    "activate": "https://your-region-your-project.cloudfunctions.net/ingestActivate",
    "counts": "https://your-region-your-project.cloudfunctions.net/ingestCounts",
    "status": "https://your-region-your-project.cloudfunctions.net/ingestStatus"
  },
  "auth_token": "your_x_api_key",
  "report_interval": 15,
  "retry_attempts": 3,
  "timeout": 10
}
```

---

## Step 4: Install Camera System

### 4.1 Transfer Files to RPi

From your Mac:

```bash
# Assuming you have camera-system-complete.tar.gz
scp camera-system-complete.tar.gz digioptics_od@192.168.0.11:/home/digioptics_od/
```

### 4.2 Extract and Setup

On the RPi:

```bash
ssh digioptics_od@192.168.0.11
cd /home/digioptics_od

# Clean previous installation
rm -rf camera-system

# Extract
mkdir camera-system
cd camera-system
tar -xzf ../camera-system-complete.tar.gz

# Make scripts executable
chmod +x *.sh
```

### 4.3 Install Python Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Install Hailo package in venv
pip install hailort
```

---

## Step 5: Run Tests

### 5.1 Test Camera

```bash
source venv/bin/activate
python3 test_camera.py
```

**Expected Output:**
```
✅ Found video devices: [0]
✅ Successfully captured frame
✅ Camera started successfully
✅ ALL TESTS PASSED
```

**Troubleshooting:**
- If no devices found: Check camera connection, run `lsusb` and `ls /dev/video*`
- If permission denied: Add user to video group: `sudo usermod -a -G video $USER`, then logout/login

### 5.2 Test Hailo Inference

```bash
python3 test_hailo_inference.py
```

**Expected Output:**
```
✅ Hailo SDK installed correctly
✅ Hailo device detected
✅ HEF file found
✅ Model loaded successfully
✅ ALL TESTS PASSED
```

**Troubleshooting:**
- **Hailo device not found:**
  - Check connection: `lsusb | grep Hailo`
  - Check drivers: `ls /dev/hailo*`
  - Reboot: `sudo reboot`

- **HEF file not found:**
  - Verify path in `config/detection_config.json`
  - Check file exists: `ls -la models/yolov8s.hef`

- **Model loading fails:**
  - Check HEF file is not corrupted
  - Verify HailoRT version compatibility
  - Check logs: `tail -f logs/inference.log`

### 5.3 Test End-to-End Pipeline

```bash
python3 test_end_to_end.py
```

**Expected Output:**
```
✅ Pipeline integration - PASS
✅ Transport - PASS
✅ Full pipeline - PASS
✅ Performance - PASS
✅ ALL TESTS PASSED - System ready for production!
```

**Performance Expectations:**
- **Inference time:** 20-50 ms per frame
- **FPS:** 20-50 FPS (depends on resolution and model)
- **10-20x faster than CPU inference**

---

## Step 6: Run Production System

### 6.1 Manual Test Run

```bash
source venv/bin/activate
python3 main.py
```

Monitor logs in separate terminal:
```bash
tail -f logs/inference.log
tail -f logs/camera.log
tail -f logs/counting.log
tail -f logs/transport.log
```

### 6.2 Install as Systemd Service

```bash
sudo ./install_service.sh
```

Control the service:
```bash
# Start
sudo systemctl start camera-detection

# Stop
sudo systemctl stop camera-detection

# Status
sudo systemctl status camera-detection

# View logs
sudo journalctl -u camera-detection -f

# Enable auto-start on boot
sudo systemctl enable camera-detection
```

### 6.3 Use REST API

Start the API server (if not using systemd):
```bash
python3 main.py --api
```

API endpoints:
```bash
# Health check
curl http://192.168.0.11:5000/health

# Start detection
curl -X POST http://192.168.0.11:5000/api/detection/start

# Check status
curl http://192.168.0.11:5000/api/detection/status

# Stop detection
curl -X POST http://192.168.0.11:5000/api/detection/stop
```

---

## Performance Tuning

### Optimize for Speed

```json
// config/camera_config.json
{
  "resolution": [1280, 720],  // Lower resolution
  "fps": 30
}

// config/detection_config.json
{
  "confidence_threshold": 0.6,  // Higher threshold = fewer detections
  "nms_threshold": 0.45
}
```

### Optimize for Accuracy

```json
// config/detection_config.json
{
  "confidence_threshold": 0.3,  // Lower threshold = more detections
  "nms_threshold": 0.3,          // Lower = keep more overlapping boxes
  "classes": ["person"]          // Focus on specific classes
}
```

### Optimize for Battery/Power

```json
// config/camera_config.json
{
  "fps": 15  // Lower FPS = less power
}

// config/backend_config.json
{
  "report_interval": 30  // Report less frequently
}
```

---

## Monitoring and Debugging

### Check Logs

```bash
# Inference performance
tail -f logs/inference.log | grep "Detected"

# Camera issues
tail -f logs/camera.log

# Firebase communication
tail -f logs/transport.log

# All logs
tail -f logs/*.log
```

### Monitor System Resources

```bash
# CPU usage
htop

# Hailo device temperature
cat /sys/class/thermal/thermal_zone*/temp

# Memory usage
free -h

# Disk space
df -h
```

### Common Issues

**1. Low FPS / Slow Inference**
- Check Hailo is being used (not CPU fallback)
- Verify HEF model is loaded (check logs)
- Reduce resolution or FPS
- Check CPU/memory usage

**2. No Detections**
- Lower confidence threshold
- Check classes filter (might be too restrictive)
- Verify camera is working (test_camera.py)
- Check model is correct for your use case

**3. Firebase Connection Fails**
- Verify internet connection
- Check auth_token is correct
- Ensure endpoints use HTTPS
- Check firewall rules

**4. Camera Disconnects**
- Check USB power (use powered hub if needed)
- Verify camera_config.json settings
- Check system logs: `dmesg | grep video`

---

## Next Steps

1. ✅ Verify all tests pass
2. ✅ Run system for 24 hours to ensure stability
3. ✅ Monitor performance metrics
4. ✅ Fine-tune configuration for your use case
5. ✅ Set up monitoring/alerting
6. ✅ Document any custom changes

---

## Model Comparison

| Model | Size | Speed (FPS) | Accuracy | Use Case |
|-------|------|-------------|----------|----------|
| YOLOv8n | ~6 MB | 50-70 | Good | Fast detection, resource-constrained |
| YOLOv8s | ~22 MB | 30-50 | Better | Balanced speed/accuracy |
| YOLOv8m | ~50 MB | 15-25 | Best | Accuracy-critical applications |

**Current Setup:** YOLOv8s (recommended for most applications)

---

## Support

- **Hailo Documentation:** https://hailo.ai/developer-zone/
- **Hailo Model Zoo:** https://github.com/hailo-ai/hailo_model_zoo
- **HailoRT Python API:** https://hailo.ai/developer-zone/documentation/hailort-python-api/

---

## Appendix: File Structure

```
camera-system/
├── agents/
│   ├── camera_agent.py              # USB camera capture
│   ├── inference_agent.py           # Legacy CPU inference (OpenCV)
│   ├── inference_agent_hailo.py     # NEW: Hailo-8 inference
│   ├── counting_agent.py            # Object counting
│   ├── transport_agent.py           # Firebase communication
│   └── orchestrator.py              # Coordinates all agents
├── config/
│   ├── camera_config.json           # Camera settings
│   ├── detection_config.json        # Model & inference settings
│   ├── counting_config.json         # Counting rules
│   └── backend_config.json          # Firebase configuration
├── models/
│   └── yolov8s.hef                  # Hailo-compiled model
├── logs/                            # Runtime logs
│   ├── camera.log
│   ├── inference.log
│   ├── counting.log
│   └── transport.log
├── test_camera.py                   # NEW: Camera test script
├── test_hailo_inference.py          # NEW: Hailo inference test
├── test_end_to_end.py               # NEW: Full pipeline test
├── main.py                          # Entry point
├── requirements.txt                 # Python dependencies
└── HAILO_SETUP_GUIDE.md             # This file
```

---

**Ready to deploy with Hailo-8! 🚀**
