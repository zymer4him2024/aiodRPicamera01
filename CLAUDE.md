# aiodRPicamera01 — Claude Code Harness

## Overview

AI Object Detection pipeline for Raspberry Pi with Hailo-8. A self-healing multi-agent system: Orchestrator manages Camera, Inference, Counting, and Transport agents with automatic health monitoring and restart. Count events are synced to Firebase Firestore and displayed on a hosted dashboard.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Agent runtime | Python 3.11 |
| AI inference | Hailo-8 NPU, YOLOv8 HEF model |
| Camera | USB camera or CSI (OpenCV `VideoCapture`) |
| Cloud backend | Firebase Firestore, Cloud Functions, Hosting, Auth |
| Dashboard | Vite + Firebase SDK |
| Deployment | Bash deploy script + systemd service |
| Auth | Firebase Auth with custom role claims (`superadmin`, tenant roles) |

---

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Start full system (orchestrator + all agents)
python startup.py

# Local GUI mode (no Hailo required)
python run_local_gui.py

# Run tests
python -m pytest tests/ -v

# Deploy to RPi
./deploy_to_rpi.sh

# Web dashboard dev
cd hosting && npm install && npm run dev

# Deploy Firebase rules + functions
firebase deploy
```

---

## Architecture

### Agent Pipeline

```
Orchestrator
  ├── Camera Agent      — captures frames from USB/CSI camera
  ├── Inference Agent   — runs YOLOv8 on Hailo-8 NPU
  ├── Counting Agent    — aggregates per-class object counts
  ├── Transport Agent   — writes count events to Firebase
  └── Handshake Agent   — device registration + keepalive
```

### Health Monitoring

Orchestrator polls each agent every 30 seconds. On failure, it restarts the agent with exponential backoff. All health metrics are exposed via REST API at `localhost:8080`.

### Firestore Data Model

| Collection | Description |
|---|---|
| `tenants/{tenantId}/counts/{docId}` | Per-detection count events |
| `tenants/{tenantId}/devices/{deviceId}` | Device registry + status |
| `users/{uid}` | User profiles with `tenantId` and role claims |

### Multitenancy

All Firestore writes include `tenantId`. Security rules enforce that users can only read/write their own tenant's data. Superadmin role bypasses tenant scoping for admin operations.

---

## Key Files

| File | Purpose |
|---|---|
| `startup.py` | Entry point — initializes Orchestrator with all agents |
| `agents/orchestrator.py` | Lifecycle manager, health checker, REST API |
| `agents/inference_agent_hailo.py` | Hailo-8 inference — loads HEF model, runs detection |
| `agents/counting_agent.py` | Count logic — per-class aggregation, crossline counting |
| `agents/transport_agent.py` | Firebase write — batch uploads with retry |
| `config/` | Environment config — device ID, Firebase project, model path |
| `deploy_to_rpi.sh` | One-command RPi deployment script |
| `deployment/aiod-camera.service` | systemd service for auto-start on boot |

---

## Environment Variables

Required in `.env` (never committed):

```env
FIREBASE_API_KEY=
FIREBASE_AUTH_DOMAIN=
FIREBASE_PROJECT_ID=
FIREBASE_STORAGE_BUCKET=
FIREBASE_MESSAGING_SENDER_ID=
FIREBASE_APP_ID=
DEVICE_ID=
TENANT_ID=
MODEL_PATH=models/model.hef
```

---

## Hardware Notes

- Hailo-8 device: `/dev/hailo0` — verify with `hailortcli fw-control identify`
- Camera: OpenCV `VideoCapture(0)` — USB camera on device index 0
- OS: Raspberry Pi OS 64-bit (Bookworm)
- Python: 3.11 with Hailo SDK installed via `hailo-all`

---

## Deployment

The `deploy_to_rpi.sh` script handles the full deployment sequence:
1. Backup existing installation
2. `rsync` all project files to RPi
3. Install Python dependencies
4. Verify Hailo-8 device access
5. Run test suite (optional)
6. Install and enable systemd service (`aiod-camera.service`)

Manual deployment steps are in [deployment_guide.md](./deployment_guide.md).

---

## Code Quality Checklist

Before completing any task:
- [ ] Agent failures handled gracefully — no bare `except` clauses
- [ ] Firestore writes include `tenantId`
- [ ] Firebase credentials from environment — never hardcoded
- [ ] New agents registered with Orchestrator for health monitoring
- [ ] Tests cover agent start/stop and main detection path
