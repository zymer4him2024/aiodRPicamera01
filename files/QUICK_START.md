# 🚀 QUICK START - Camera Detection System

## What You Have

A complete, production-ready AI object detection system with:
- ✅ Modular Python agents (camera, inference, counting, transport)
- ✅ CPU inference with OpenCV DNN + YOLOv8
- ✅ Firebase Cloud Functions integration
- ✅ REST API for remote control
- ✅ Systemd service for auto-start
- ✅ Comprehensive error handling and logging
- ✅ Easy upgrade path to Hailo-8

## File: camera-system-complete.tar.gz

Download this file and transfer to your Raspberry Pi.

---

## 5-Minute Deployment

### 1. Transfer to RPi (On Mac)

```bash
scp camera-system-complete.tar.gz digioptics_od@192.168.0.11:/home/digioptics_od/
```

### 2. Extract and Deploy (On RPi)

```bash
ssh digioptics_od@192.168.0.11
cd /home/digioptics_od
rm -rf camera-system
mkdir camera-system
cd camera-system
tar -xzf ../camera-system-complete.tar.gz
chmod +x *.sh
./deploy.sh
```

### 3. Configure Firebase

```bash
nano config/backend_config.json
```

Update:
- `camera_id`: Your unique camera ID
- `site_id`: Your site ID  
- `auth_token`: Your Firebase X-API-Key

Save: Ctrl+X → Y → Enter

### 4. Test

```bash
source venv/bin/activate
./test_components.sh
```

### 5. Run

```bash
# Manual test
python3 main.py

# Or install as service
sudo ./install_service.sh
sudo systemctl start camera-detection
```

### 6. Control

```bash
# Start detection
curl -X POST http://192.168.0.11:5000/api/detection/start

# Check status
curl http://192.168.0.11:5000/api/detection/status
```

---

## File Structure

```
camera-system/
├── config/
│   ├── camera_config.json       # Camera settings
│   ├── detection_config.json    # AI model settings
│   ├── counting_config.json     # Counting rules
│   └── backend_config.json      # Firebase settings
├── agents/
│   ├── camera_agent.py          # USB camera capture
│   ├── inference_agent.py       # CPU inference (OpenCV DNN)
│   ├── counting_agent.py        # Object counting
│   ├── transport_agent.py       # Firebase communication
│   └── orchestrator.py          # Coordinates all agents
├── api/
│   └── detection_api.py         # Flask REST API
├── utils/
│   ├── config_loader.py         # Config utilities
│   └── logger.py                # Logging utilities
├── main.py                      # Entry point
├── deploy.sh                    # Deployment script
├── test_components.sh           # Test script
├── install_service.sh           # Systemd installer
├── requirements.txt             # Python dependencies
├── README.md                    # Full documentation
└── DEPLOYMENT_GUIDE.md          # Step-by-step guide
```

---

## Key Features

### Security
- ✅ HTTPS-only endpoints
- ✅ X-API-Key authentication
- ✅ SSL certificate validation
- ✅ No hardcoded secrets

### Reliability
- ✅ Exponential backoff retry logic
- ✅ Graceful error handling
- ✅ Resource cleanup on shutdown
- ✅ Auto-restart on failure (systemd)

### Performance
- ✅ ~2-5 FPS on RPi 5 CPU
- ✅ Configurable report intervals
- ✅ Efficient model inference
- ✅ Ready for Hailo upgrade (10-20x faster)

### Monitoring
- ✅ Comprehensive logging
- ✅ REST API status endpoint
- ✅ Systemd journal integration
- ✅ Health check endpoint

---

## API Endpoints

**Start Detection:**
```bash
POST http://192.168.0.11:5000/api/detection/start
```

**Stop Detection:**
```bash
POST http://192.168.0.11:5000/api/detection/stop
```

**Get Status:**
```bash
GET http://192.168.0.11:5000/api/detection/status
```

**Health Check:**
```bash
GET http://192.168.0.11:5000/health
```

---

## Configuration Examples

### Detect Only People
```json
// config/detection_config.json
{
  "classes": ["person"]
}
```

### Count People with High Confidence
```json
// config/counting_config.json
{
  "classes_to_count": ["person"],
  "min_confidence": 0.7
}
```

### Report Every 30 Seconds
```json
// config/backend_config.json
{
  "report_interval": 30
}
```

---

## Troubleshooting

**Camera not working:**
```bash
ls -la /dev/video*
# Update device_id in config/camera_config.json
```

**Model download slow:**
- First run downloads YOLOv8n (~6MB)
- Takes 2-3 minutes on RPi
- Cached for future runs

**Firebase not receiving data:**
- Check X-API-Key is correct
- Verify endpoint URL
- Check logs: `tail -f logs/transport.log`

**High CPU usage:**
- Reduce FPS in camera_config.json
- Increase report_interval in backend_config.json
- Consider Hailo upgrade

---

## Next Steps

1. ✅ Deploy to RPi
2. ✅ Verify Firebase integration
3. ✅ Monitor for 24 hours
4. ✅ Fine-tune configurations
5. ✅ Plan Hailo upgrade for production

---

## Upgrading to Hailo

The system is designed for easy Hailo upgrade:

1. Install Hailo SDK
2. Convert model to .hef
3. Replace only `agents/inference_agent.py`
4. Update `detection_config.json`
5. Restart service

**10-20x performance improvement with minimal code changes!**

---

**Full documentation in DEPLOYMENT_GUIDE.md**

**Ready to deploy! 🎯**
