# Full Automation Guide - Camera Detection System

Complete guide for fully automated deployment and operation with agent-based architecture.

---

## Architecture Overview

### Agent Hierarchy

```
┌─────────────────────────────────────────────────────────┐
│                  ORCHESTRATOR AGENT                     │
│  - Lifecycle management                                 │
│  - Health monitoring                                    │
│  - Auto-restart failed agents                           │
│  - Metrics collection                                   │
└────────────┬────────────────────────────────────────────┘
             │
    ┌────────┴────────┬──────────────┬─────────────────┐
    │                 │              │                 │
┌───▼───┐      ┌──────▼──────┐  ┌───▼────┐     ┌─────▼──────┐
│CAMERA │      │  INFERENCE  │  │COUNTING│     │ TRANSPORT  │
│AGENT  │─────>│   AGENT     │─>│ AGENT  │────>│   AGENT    │
│       │      │  (Hailo-8)  │  │        │     │ (Firebase) │
└───────┘      └─────────────┘  └────────┘     └────────────┘
```

### Key Features

✅ **Fully Autonomous** - Runs without human intervention
✅ **Self-Healing** - Auto-restarts failed agents
✅ **Health Monitoring** - Continuous agent health checks
✅ **Performance Tracking** - Real-time metrics
✅ **Remote Control** - REST API for management
✅ **Auto-Deploy** - One-command deployment to RPi

---

## Quick Start - Automated Deployment

### From Your Mac

```bash
# 1. Navigate to project
cd "/Users/shawnshlee/1_Claude Code/AI OD RPiv01"

# 2. Run auto-deploy script
./deploy_to_rpi.sh

# That's it! The script will:
# - Backup existing installation
# - Sync all files to RPi
# - Install dependencies
# - Verify Hailo/camera
# - Optionally run tests
```

### Manual Deployment

If you prefer manual control:

```bash
# Transfer files
scp -r camera-system digioptics_od@192.168.0.11:/home/digioptics_od/

# SSH to RPi
ssh digioptics_od@192.168.0.11

# Setup
cd camera-system
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Install service
sudo ./install_service.sh
```

---

## Operation Modes

### 1. Standalone Mode (Manual Testing)

Run directly for testing:

```bash
cd /home/digioptics_od/camera-system
source venv/bin/activate
python3 main.py
```

**Features:**
- Interactive console output
- Easy to stop (Ctrl+C)
- Immediate feedback
- Good for debugging

**Logs:** Console + `/home/digioptics_od/camera-system/logs/`

---

### 2. API Mode (Remote Control)

Run with REST API for remote management:

```bash
python3 main.py --api --host 0.0.0.0 --port 5000
```

**API Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/api/detection/start` | Start detection |
| POST | `/api/detection/stop` | Stop detection |
| POST | `/api/detection/pause` | Pause detection |
| POST | `/api/detection/resume` | Resume detection |
| GET | `/api/detection/status` | Get system status |
| GET | `/api/config/<component>` | Get configuration |

**Usage Examples:**

```bash
# Health check
curl http://192.168.0.11:5000/health

# Start detection
curl -X POST http://192.168.0.11:5000/api/detection/start

# Get status
curl http://192.168.0.11:5000/api/detection/status

# Get camera config
curl http://192.168.0.11:5000/api/config/camera
```

**Auto-start with API:**

```bash
python3 main.py --api --autostart
```

---

### 3. Service Mode (Production - Fully Automated)

Install as systemd service for complete automation:

```bash
sudo ./install_service.sh
```

**Service Commands:**

```bash
# Start service
sudo systemctl start camera-detection

# Stop service
sudo systemctl stop camera-detection

# Restart service
sudo systemctl restart camera-detection

# Check status
sudo systemctl status camera-detection

# View live logs
sudo journalctl -u camera-detection -f

# Enable auto-start on boot (already enabled by install script)
sudo systemctl enable camera-detection

# Disable auto-start
sudo systemctl disable camera-detection
```

**Service Features:**
- ✅ Auto-starts on boot
- ✅ Auto-restarts on failure (10-second delay)
- ✅ Runs in background (daemon)
- ✅ Systemd journal logging
- ✅ Resource limits (1GB RAM, 200% CPU)
- ✅ Proper signal handling
- ✅ Security hardening

---

## Agent Details

### Orchestrator Agent

**File:** `agents/orchestrator.py`

**Responsibilities:**
- Initialize and start all sub-agents
- Coordinate data flow between agents
- Monitor agent health (every 30 seconds)
- Auto-restart failed agents
- Collect and log metrics
- Handle graceful shutdown

**Threads:**
1. **Detection Thread** - Captures frames, runs inference, queues detections
2. **Reporting Thread** - Aggregates detections, sends to Firebase
3. **Health Monitor Thread** - Checks agent status, restarts if needed

**Metrics Tracked:**
- Frames processed
- Detection count
- Reports sent
- Errors encountered
- Uptime
- Last report time

---

### Camera Agent

**File:** `agents/camera_agent.py`

**Responsibilities:**
- Initialize USB/CSI camera
- Capture frames continuously
- Thread-safe frame access
- Auto-retry on failure (3 attempts)
- Frame validation

**Health Indicators:**
- `cap` object exists and is open
- Frames are valid 3D BGR arrays

---

### Inference Agent (Hailo-8)

**File:** `agents/inference_agent_hailo.py`

**Responsibilities:**
- Load HEF model on Hailo-8
- Preprocess frames (resize, normalize, BGR→RGB)
- Run inference on Hailo accelerator
- Post-process outputs (NMS, class filtering)
- Return detections in standard format

**Health Indicators:**
- `is_ready()` returns True
- VDevice connected
- Model loaded

**Performance:**
- 20-50 FPS on Hailo-8
- 20-50ms inference time

---

### Counting Agent

**File:** `agents/counting_agent.py`

**Responsibilities:**
- Count detected objects by class
- Filter by confidence threshold
- Aggregate counts over time
- Format for Firebase

**Health Indicators:**
- Always healthy (stateless processing)

---

### Transport Agent

**File:** `agents/transport_agent.py`

**Responsibilities:**
- Send counts to Firebase Cloud Functions
- Send activation signals
- Send status updates
- Exponential backoff retry logic
- HTTPS-only enforcement

**Health Indicators:**
- Can connect to Firebase endpoints
- Valid auth token

---

## Auto-Restart Behavior

### Agent-Level Auto-Restart

The **Health Monitor Thread** checks agent health every 30 seconds:

```python
# Camera health check
if camera is unhealthy:
    stop camera
    wait 2 seconds
    start camera

# Inference health check
if inference is unhealthy:
    unload model
    wait 2 seconds
    load model
```

### System-Level Auto-Restart

The **systemd service** provides system-level resilience:

```ini
Restart=always
RestartSec=10
```

If the entire process crashes:
1. systemd waits 10 seconds
2. Restarts main.py automatically
3. Orchestrator reinitializes all agents
4. System resumes operation

---

## Monitoring and Logs

### Log Files

All logs in `/home/digioptics_od/camera-system/logs/`:

| File | Content |
|------|---------|
| `orchestrator.log` | Main coordination, metrics, health checks |
| `camera.log` | Frame capture, camera errors |
| `inference.log` | Model loading, inference performance |
| `counting.log` | Detection counting |
| `transport.log` | Firebase communication, retries |
| `main.log` | Top-level entry point |

### View Logs

```bash
# All logs
tail -f logs/*.log

# Orchestrator only
tail -f logs/orchestrator.log

# Inference performance
tail -f logs/inference.log | grep "Performance"

# Firebase status
tail -f logs/transport.log

# Systemd journal (if running as service)
sudo journalctl -u camera-detection -f
```

### Metrics

The orchestrator logs metrics every 60 seconds:

```
Status: Uptime=3600s, Frames=7200, Reports=240
```

**Interpretation:**
- **Uptime:** System running for 1 hour
- **Frames:** Processed 7200 frames (2 FPS average)
- **Reports:** Sent 240 reports to Firebase

---

## Configuration

All configuration in `config/` directory:

### `camera_config.json`
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

### `detection_config.json`
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

### `counting_config.json`
```json
{
  "method": "simple_count",
  "classes_to_count": ["person", "car", "truck", "bus", "motorcycle"],
  "min_confidence": 0.6,
  "zones": []
}
```

### `backend_config.json`
```json
{
  "camera_id": "cam_001",
  "site_id": "site_001",
  "endpoints": {
    "activate": "https://...",
    "counts": "https://...",
    "status": "https://..."
  },
  "auth_token": "your_key",
  "report_interval": 15,
  "retry_attempts": 3,
  "timeout": 10
}
```

**To modify:** Edit files and restart service:
```bash
sudo systemctl restart camera-detection
```

---

## Deployment Workflow

### Development → Production Flow

```bash
# 1. Develop locally on Mac
cd "/Users/shawnshlee/1_Claude Code/AI OD RPiv01/camera-system"
# Edit agents, configs, etc.

# 2. Deploy to RPi automatically
cd ..
./deploy_to_rpi.sh

# 3. Script will:
#    - Create backup on RPi
#    - Stop service if running
#    - Sync all files
#    - Install dependencies
#    - Set permissions
#    - Verify hardware
#    - Optionally run tests

# 4. If tests pass, install service
ssh digioptics_od@192.168.0.11
cd camera-system
sudo ./install_service.sh

# 5. Monitor
sudo journalctl -u camera-detection -f
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check service status
sudo systemctl status camera-detection

# Check logs
sudo journalctl -u camera-detection -n 50

# Check permissions
ls -la /home/digioptics_od/camera-system

# Verify venv
ls -la /home/digioptics_od/camera-system/venv
```

### Agents Keep Restarting

```bash
# Check orchestrator log
tail -f logs/orchestrator.log

# Look for health check failures
grep "unhealthy" logs/orchestrator.log

# Check specific agent
tail -f logs/camera.log
tail -f logs/inference.log
```

### No Detections

```bash
# Verify Hailo is working
lsusb | grep Hailo
ls /dev/hailo*

# Check inference log
tail -f logs/inference.log

# Test inference manually
source venv/bin/activate
python3 test_hailo_inference.py
```

### Firebase Not Receiving Data

```bash
# Check transport log
tail -f logs/transport.log

# Verify config
cat config/backend_config.json

# Test endpoint manually
curl -X POST https://your-endpoint \
  -H "X-API-Key: your_key" \
  -H "Content-Type: application/json" \
  -d '{"test": true}'
```

---

## Performance Tuning

### High CPU Usage

```bash
# Reduce FPS
nano config/camera_config.json
# Set "fps": 15

# Reduce resolution
# Set "resolution": [1280, 720]

# Restart
sudo systemctl restart camera-detection
```

### Low FPS

```bash
# Verify Hailo is active
tail -f logs/inference.log | grep "Hailo"

# Check CPU usage
htop

# Increase report interval (less Firebase overhead)
nano config/backend_config.json
# Set "report_interval": 30
```

### Memory Issues

```bash
# Check memory usage
free -h

# Service has 1GB limit, increase if needed
sudo nano /etc/systemd/system/camera-detection.service
# Change: MemoryLimit=2G

sudo systemctl daemon-reload
sudo systemctl restart camera-detection
```

---

## Security Notes

### Service Security

The systemd service includes security hardening:

```ini
NoNewPrivileges=true   # Prevent privilege escalation
PrivateTmp=true        # Isolated /tmp directory
```

### API Security

If running in API mode:
- Consider adding authentication
- Use HTTPS with reverse proxy (nginx)
- Restrict access with firewall

Example nginx reverse proxy:

```nginx
server {
    listen 443 ssl;
    server_name camera.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## Summary

You now have a **fully automated, self-healing camera detection system**:

✅ **Agent-based architecture** - Modular, maintainable
✅ **Auto-deployment** - One command from Mac to RPi
✅ **Self-healing** - Agents auto-restart on failure
✅ **Health monitoring** - Continuous checks every 30s
✅ **Multiple operation modes** - Standalone, API, Service
✅ **Production-ready** - systemd integration, logging, metrics
✅ **Hailo-8 accelerated** - 20-50 FPS performance
✅ **Firebase integration** - Cloud data upload
✅ **Remote control** - REST API
✅ **Well documented** - Complete guides and examples

**Next Steps:**
1. Run `./deploy_to_rpi.sh` from Mac
2. Let it install and test
3. Install service with `sudo ./install_service.sh`
4. Monitor with `sudo journalctl -u camera-detection -f`
5. Enjoy fully automated operation!
