# Quick Test Guide - Hailo Camera Inference

Fast reference for testing camera inference on Raspberry Pi with Hailo-8.

---

## Pre-flight Checks

```bash
# 1. Check Hailo device
lsusb | grep Hailo
ls /dev/hailo*

# 2. Check camera
ls /dev/video*

# 3. Check model file
ls -lh models/yolov8s.hef
```

---

## Run Tests (In Order)

### Test 1: Camera Only (30 seconds)
```bash
cd /home/digioptics_od/camera-system
source venv/bin/activate
python3 test_camera.py
```

**Look for:** `✅ ALL TESTS PASSED`

### Test 2: Hailo Inference (1 minute)
```bash
python3 test_hailo_inference.py
```

**Look for:**
- `✅ Hailo device detected`
- `✅ Model loaded successfully`
- `Avg inference time: 20-50 ms`
- `FPS: 20-50`

### Test 3: Full Pipeline (2 minutes)
```bash
python3 test_end_to_end.py
```

**Look for:**
- Multiple object detections
- Firebase uploads (if configured)
- Stable FPS

---

## Quick Run

```bash
# Activate environment
source venv/bin/activate

# Run detection
python3 main.py

# Watch logs (separate terminal)
tail -f logs/inference.log
```

**Stop:** Press `Ctrl+C`

---

## Troubleshooting

### Hailo Not Detected
```bash
# Reboot
sudo reboot

# After reboot, check again
lsusb | grep Hailo
```

### Model Not Found
```bash
# Check path in config
cat config/detection_config.json | grep model_path

# Verify file exists
ls -la models/
```

### Camera Not Working
```bash
# Find camera device
ls -la /dev/video*

# Update config
nano config/camera_config.json
# Change "device_id": 0 to appropriate number
```

### Low FPS
```bash
# Check if using Hailo (not CPU)
tail -f logs/inference.log

# Should see "Hailo-8" in logs, not "OpenCV DNN"
```

---

## Configuration Quick Edits

### Use Different Camera
```bash
nano config/camera_config.json
# Change: "device_id": 0
```

### Detect Only People
```bash
nano config/detection_config.json
# Change: "classes": ["person"]
```

### Change Confidence Threshold
```bash
nano config/detection_config.json
# Change: "confidence_threshold": 0.5  (0.0-1.0)
```

---

## Service Commands

```bash
# Start service
sudo systemctl start camera-detection

# Stop service
sudo systemctl stop camera-detection

# Status
sudo systemctl status camera-detection

# Logs
sudo journalctl -u camera-detection -f
```

---

## API Commands

```bash
# Start
curl -X POST http://192.168.0.11:5000/api/detection/start

# Status
curl http://192.168.0.11:5000/api/detection/status

# Stop
curl -X POST http://192.168.0.11:5000/api/detection/stop
```

---

## Expected Performance

| Metric | Value |
|--------|-------|
| Inference Time | 20-50 ms |
| FPS | 20-50 |
| CPU Usage | 30-50% |
| Memory | ~500 MB |

**If performance is worse:** Check logs, verify Hailo is active, reduce resolution

---

## Files to Check

```bash
# Configuration
ls -la config/*.json

# Logs
ls -la logs/*.log

# Model
ls -la models/*.hef

# Test scripts
ls -la test_*.py
```

---

## One-Liner Full Test

```bash
source venv/bin/activate && python3 test_camera.py && python3 test_hailo_inference.py && python3 test_end_to_end.py
```

---

**For detailed guide, see: HAILO_SETUP_GUIDE.md**
