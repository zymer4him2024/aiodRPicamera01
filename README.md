# aiodRPicamera01

![Edge AI](https://img.shields.io/badge/Edge%20AI-Hailo--8-blue)
![Platform](https://img.shields.io/badge/Platform-Raspberry%20Pi-red)
![Agents](https://img.shields.io/badge/Architecture-Multi--Agent-blueviolet)
![Firebase](https://img.shields.io/badge/Backend-Firebase-FFCA28)
![Status](https://img.shields.io/badge/Status-Deployment%20Ready-brightgreen)
![License](https://img.shields.io/badge/License-MIT-green)
![Claude Code](https://img.shields.io/badge/Dev%20OS-Claude%20Code-blueviolet)

AI Object Detection pipeline for Raspberry Pi with Hailo-8 camera system. A self-healing multi-agent architecture: an Orchestrator manages the lifecycle of Camera, Inference, Counting, and Transport agents, with automatic restart on failure and one-command deployment to any RPi target.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR AGENT                       │
│  Lifecycle management, health monitoring, auto-restart,     │
│  metrics collection, REST API for remote control            │
└────────────┼─────────────┼────────────┼─────────────────┘
             │              │              │
    ┌─────────┼──┐  ┌──────┼──────┐  ┌───┼────┐  ┌─────────┼─────┐
    │   CAMERA   │  │  INFERENCE   │  │COUNTING│  │   TRANSPORT    │
    │   AGENT    │─▶│    AGENT     │─▶│ AGENT  │─▶│     AGENT      │
    │ USB/CSI    │  │  Hailo-8     │  │ Object │  │ Firebase Cloud │
    │ capture    │  │  YOLOv8      │  │ aggr.  │  │ Functions sync │
    └────────────┘  └─────────────┘  └────────┘  └────────────────┘
                                                         │
                                              ┌─────────┼──────────┐
                                              │  Firebase Firestore  │
                                              │  + Hosting Dashboard │
                                              └─────────────────────┘
```

### Agent Responsibilities

| Agent | File | Role |
|---|---|---|
| Orchestrator | `agents/orchestrator.py` | Lifecycle, health checks, auto-restart |
| Camera | `agents/camera_agent.py` | USB/CSI camera frame capture |
| Inference | `agents/inference_agent_hailo.py` | Hailo-8 accelerated YOLOv8 inference |
| Counting | `agents/counting_agent.py` | Object count aggregation + crossline logic |
| Transport | `agents/transport_agent.py` | Firebase Cloud Functions upload |
| Handshake | `agents/handshake_agent.py` | Device registration + keepalive |

---

## Key Features

- **Fully autonomous** — runs without human intervention after deployment
- **Self-healing** — Orchestrator auto-restarts failed agents with backoff
- **Health monitoring** — continuous 30-second health checks across all agents
- **One-command deployment** — `./deploy_to_rpi.sh` syncs, installs, and verifies on any RPi
- **Systemd service** — auto-start on boot, auto-restart on crash
- **REST API** — remote start/stop/status/config endpoints via Orchestrator
- **Multitenant** — `tenantId` scoped Firestore writes and Firebase rules

---

## Tech Stack

| Layer | Technology |
|---|---|
| Agent runtime | Python 3.11 |
| AI inference | Hailo-8 (hardware NPU), YOLOv8 |
| Cloud backend | Firebase Firestore, Cloud Functions, Hosting |
| Web dashboard | Vite + Firebase SDK (Hosting) |
| Deployment | Bash + systemd (`aiod-camera.service`) |
| Auth | Firebase Auth with superadmin role support |

---

## Quick Start

### Deploy to Raspberry Pi

```bash
# From your Mac/dev machine
./deploy_to_rpi.sh

# The script will:
# - Backup existing installation on RPi
# - Sync all files via rsync
# - Install Python dependencies
# - Verify Hailo-8 device
# - Optionally run test suite
# - Install and enable systemd service
```

### Run Locally (Development)

```bash
pip install -r requirements.txt
python startup.py          # Start orchestrator + all agents
python run_local_gui.py    # Local GUI mode (no Hailo required)
```

### Run Tests

```bash
python -m pytest tests/ -v
```

### API Control

```bash
# Health check
curl http://localhost:8080/health

# Agent status
curl http://localhost:8080/status

# Stop all agents
curl -X POST http://localhost:8080/stop

# Start all agents
curl -X POST http://localhost:8080/start
```

---

## Project Structure

```
aiodRPicamera01/
├── agents/                    — Agent implementations
│   ├── orchestrator.py        — Master lifecycle agent
│   ├── camera_agent.py
│   ├── inference_agent_hailo.py
│   ├── counting_agent.py
│   ├── transport_agent.py
│   └── handshake_agent.py
├── backend/                   — Firebase Functions + Firestore rules
├── hosting/                   — Web dashboard (Vite)
├── camera-system/             — Camera configuration
├── config/                    — Environment + device config
├── deployment/                — systemd service files
├── docs/                      — Deployment and setup guides
├── scripts/                   — Utility scripts
├── tests/                     — Full test suite
├── startup.py                 — Main entry point
├── main.py                    — Alternative entry point
├── deploy_to_rpi.sh           — One-command RPi deployment
└── requirements.txt
```

---

## Ecosystem Position

aiodRPicamera01 is the **reference edge inference implementation** for the Antigravity platform — the canonical multi-agent pattern that SurgicalAI01 and Detection2Robotics01 extend for their specific domains.

```
TeleiosAI01 (Studio)  →  model.hef + labels.json
                                   ↓
             aiodRPicamera01 (RPi5 + Hailo-8)
             ┌────────────────────────────────────────┐
             │ Orchestrator                              │
             │   ├── Camera Agent                       │
             │   ├── Inference Agent (Hailo-8)          │
             │   ├── Counting Agent                     │
             │   ├── Transport Agent ────────────────┬│
             │   └── Handshake Agent                    ││
             └───────────────────────────────────────┘│
                                                        ↓
                                    Firebase Firestore (count events)
                                                        ↓
                                AI OD Counter Multitenant (dashboard)
```

| Role | Project | Connection |
|---|---|---|
| Model factory | [TeleiosAI01](https://github.com/zymer4him2024/teleiosai01) | Produces `model.hef` + `labels.json` loaded by the Inference Agent |
| Count visualization | [AI OD Counter Multitenant](https://github.com/zymer4him2024/ai-od-counter-multitenant) | Consumes Firestore count events written by Transport Agent |
| Surgical extension | [SurgicalAI01](https://github.com/zymer4him2024/surgicalai01) | Extends this architecture with a Gateway state machine, HDMI HUD, and Device Master |
| Robotics extension | [Detection2Robotics01](https://github.com/zymer4him2024/detection2robotics01) | Extends this architecture with Coordinator + RTDE robot actuation |
| UI design system | [ui-platform](https://github.com/zymer4him2024/ui-platform) | Design tokens for the hosted Vite dashboard |

---

## Harness Engineering

Claude Code drives development with `CLAUDE.md` as the system configuration contract. The harness encodes the Orchestrator authority model (only the Orchestrator manages agent lifecycles), Firestore tenant isolation requirements, and deployment pipeline contracts.

This repo is the **reference implementation** for Hailo-8 edge inference on Raspberry Pi. The agent architecture pattern here is the template consumed by SurgicalAI01 and Detection2Robotics01.

---

## Documentation

| Document | Description |
|---|---|
| [CLAUDE.md](./CLAUDE.md) | AI assistant context, architecture decisions |
| [AUTOMATION_GUIDE.md](./AUTOMATION_GUIDE.md) | Agent architecture and automation details |
| [DEPLOYMENT_READY.md](./DEPLOYMENT_READY.md) | What is built and ready to deploy |
| [HAILO_CAMERA_READY.md](./HAILO_CAMERA_READY.md) | Hailo-8 + camera setup status |
| [deployment_guide.md](./deployment_guide.md) | Step-by-step deployment guide |

---

## Engineering Standards

- SOLID agent separation — each agent has a single, well-defined responsibility
- Orchestrator is the only agent with lifecycle authority over others
- Firebase credentials via environment variables only — never committed
- Systemd service ensures system-level reliability on RPi hardware
- Firestore security rules enforce per-tenant data isolation
