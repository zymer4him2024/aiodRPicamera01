# aiodRPicamera01 — Claude Code Harness

## Harness Engineering Context

This file is the **Claude Code harness** for aiodRPicamera01. Read as system configuration before every development session.

**Critical invariants:**
- The Orchestrator is the ONLY agent with lifecycle authority — no agent may start/stop another agent directly
- All Firestore writes must include `tenantId` — no exceptions
- Firebase credentials from environment variables only — never hardcoded
- New agents MUST be registered with the Orchestrator for health monitoring
- Agent failures must be handled gracefully — no bare `except` clauses that swallow errors silently

**Orchestrator Pattern (do not break this contract):**
```
Orchestrator
  ├── starts all agents on startup
  ├── polls health every 30s
  ├── restarts failed agents with exponential backoff
  └── exposes REST API for external control (start/stop/status/config)
```
Any change to agent startup, lifecycle, or communication must go through the Orchestrator API — never bypass it.

**If a constraint seems wrong, update this file explicitly. Do not work around it.**

---

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

## Troubleshooting Ledger

Numbered log of real issues encountered and fixed. Never re-introduce a resolved issue.

1. **Hailo-8 device `/dev/hailo0` not found after reboot**: The `hailo-all` package installs the kernel module but it may not load automatically if the DKMS installation was interrupted. Fix: `sudo modprobe hailo_pci` loads the module immediately. Verify with `ls /dev/hailo0` and `hailortcli fw-control identify`. For persistence across reboots, add `hailo_pci` to `/etc/modules`.

2. **Camera `VideoCapture(0)` opens but returns empty frames**: USB cameras need a 1–2 second warm-up after `cap = cv2.VideoCapture(0)`. Reading a frame immediately on startup returns a black frame. Fix: add a 2-second sleep before the first `cap.read()` in `camera_agent.py`, or discard the first 5 frames in the capture loop.

3. **Orchestrator marking inference agent as failed immediately after start**: If Hailo SDK model loading takes >30s on a cold boot (model not in cache), the Orchestrator's 30-second health-check fires before the agent is ready and marks it as failed. Fix: increase `HEALTH_CHECK_TIMEOUT` in Orchestrator config to 90s for the initial startup window; drop back to 30s once the agent reports healthy for the first time.

4. **`tenantId` missing from Firestore writes, writes silently rejected**: The transport agent was writing count events without `tenantId` when `TENANT_ID` env var was not set. Firestore rules reject these writes with no error visible in the dashboard. Fix: add a startup assertion in `transport_agent.py` that raises `EnvironmentError` if `TENANT_ID` is empty — fail loudly at startup rather than silently drop data. Check `.env` file is present on the RPi (it is not synced by `deploy_to_rpi.sh` by default).

5. **RPi5 thermal throttle degrading inference latency under sustained load**: Hailo-8 PCIe + USB camera + active inference can push RPi5 above 85°C in warm environments. When the RPi5 throttles, inference latency increases from ~15ms to >100ms, causing the Orchestrator to flag the inference agent as slow. Fix: configure `arm_boost=1` and `over_voltage_delta=50000` in `/boot/firmware/config.txt` for stable 2.4GHz operation, and ensure the case has active airflow across the Hailo-8 M.2 module.

6. **systemd service enters restart loop immediately after `deploy_to_rpi.sh`**: The deploy script restarts the service before `pip install -r requirements.txt` finishes, causing an `ImportError` on newly-added dependencies. The service then hits the systemd restart limit within 2 minutes. Fix: ensure `pip install` completes before `systemctl restart aiod-camera.service` in the deploy script. Also add `RestartSec=5s` to the `.service` file to add breathing room on crash-restart cycles.

7. **Counting agent double-counting objects crossing a counting line**: When frame rate temporarily exceeds downstream processing throughput, duplicate detection events arrive for the same object crossing. Fix: add a per-class cooldown timer in `counting_agent.py` (`COOLDOWN_MS=500` default) — once a class crossing is registered, no second crossing for the same class can fire within the cooldown window.

8. **Transport agent `batch.commit()` failing on first run with permission denied**: The Firestore client initializes asynchronously. If the transport agent fires its first batch commit before the Firebase Auth token is fully ready, the write fails with a permission error. Fix: add retry logic with 3 attempts and 2-second backoff around `batch.commit()` in the transport agent. Ensure `initializeApp()` in `startup.py` completes and the token is confirmed before any agent thread starts.

9. **`deploy_to_rpi.sh` fails with `Permission denied` on Docker group commands**: The deploy script runs `docker compose` but the RPi user was added to the `docker` group in a previous session. The current shell doesn't have the group active yet. Fix: the deploy script should re-launch itself under the docker group context using `exec sg docker -c "bash $0 $@"` to avoid requiring a logout/login cycle.

10. **Handshake agent keepalive loop flooding Firestore writes**: If `KEEPALIVE_INTERVAL_SEC` is set too low (e.g., 5s instead of the intended 60s), the handshake agent creates one Firestore write every 5 seconds per device. At scale this triggers Firestore rate-limit warnings. Fix: enforce a minimum of `KEEPALIVE_INTERVAL_SEC=30` in the handshake agent config, and default to 60s. Log a warning if the configured value is below the minimum.

---

## Code Quality Checklist

Before completing any task:
- [ ] Agent failures handled gracefully — no bare `except` clauses
- [ ] Firestore writes include `tenantId`
- [ ] Firebase credentials from environment — never hardcoded
- [ ] New agents registered with Orchestrator for health monitoring
- [ ] Tests cover agent start/stop and main detection path

---

## Ecosystem Position

aiodRPicamera01 is the **reference edge inference implementation** for the Antigravity platform.

```
TeleiosAI01 (Studio)  →  model.hef
                               ↓
                     aiodRPicamera01 (loads HEF)
                     Orchestrator → Camera → Inference → Counting → Transport
                               ↓
                     Firebase Firestore (count events)
                               ↓
                     AI OD Counter Multitenant (dashboard)
```

The architecture here (Orchestrator + named agents + Firestore transport) is the template for SurgicalAI01 and Detection2Robotics01.

## ui-platform Alignment

The hosted dashboard (in `hosting/`) should follow the Antigravity shared design system:
- Import components from `@repo/ui` when migrating to a framework
- Use `MonitoringView` template for count dashboard
- Design tokens: brand blue #3b82f6, Inter font, Zinc neutrals, 4px spacing grid
- Reference [ui-platform CLAUDE.md](https://github.com/zymer4him2024/ui-platform/blob/main/CLAUDE.md)
