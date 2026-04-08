# RPi-Backend Handshake Test Guide

## Overview

This document describes how to test the handshake between an RPi device and the Firebase backend. The handshake allows RPi devices to self-register using QR code tokens.

## Architecture

```
┌─────────────────┐                              ┌──────────────────┐
│     RPi         │                              │    Firebase      │
│   (Standalone)  │                              │    Backend       │
└────────┬────────┘                              └────────┬─────────┘
         │                                                │
         │  1. Load QR payload (token, backend_url)       │
         │                                                │
         │  2. POST /api/device/register                  │
         │     {serial, token, ip}                        │
         ├───────────────────────────────────────────────►│
         │                                                │
         │  3. Validate token, register camera            │
         │     Return binding config                      │
         │◄───────────────────────────────────────────────┤
         │                                                │
         │  4. Save binding.json locally                  │
         │  5. POST /api/device/activate                  │
         │     {serial, status: "active"}                 │
         ├───────────────────────────────────────────────►│
         │                                                │
         │  6. Camera marked active                       │
         │◄───────────────────────────────────────────────┤
         │                                                │
         ▼                                                ▼
    [BOUND]                                         [CAMERA ACTIVE]
```

## Prerequisites

### Backend (Already Deployed)
- ✅ Firebase Functions deployed to `aiodcounter06`
- ✅ HandshakeAgent implemented
- ✅ Endpoints available:
  - `POST /api/device/register` - Device self-registration
  - `POST /api/device/activate` - Activation ping
  - `POST /api/dev/seed-token` - Dev: Create test tokens

### RPi
- ✅ Python 3.x with `requests` module
- ✅ HandshakeAgent (`agents/handshake_agent.py`)
- ✅ BindingManager (`utils/binding_manager.py`)

## Test Token Information

**Token:** `c7979e050518223bedea817d510ac48819b98a9b90efc633ed586da956534ea1`
**Site ID:** `global-innovation-anaheim-001`
**Org ID:** `global-innovation`
**Expires:** 2026-01-16T22:11:00Z (48 hours from creation)
**Status:** Ready in Firestore ✅

## Step-by-Step Testing

### Step 1: Copy Files to RPi

```bash
# From your local machine, copy the project to RPi
scp -r /Users/shawnshlee/1_Antigravity/1_Antig_aiodcounter01/* pi@<rpi-ip>:~/aiodcounter01/

# Or just copy the essential files:
scp config/qr_payload.json pi@<rpi-ip>:~/aiodcounter01/config/
scp agents/handshake_agent.py pi@<rpi-ip>:~/aiodcounter01/agents/
scp tests/test_handshake.py pi@<rpi-ip>:~/aiodcounter01/tests/
```

### Step 2: Verify QR Payload on RPi

```bash
# SSH into RPi
ssh pi@<rpi-ip>

# Navigate to project
cd ~/aiodcounter01

# Check the QR payload
cat config/qr_payload.json
```

Expected output:
```json
{
    "backend_url": "https://us-central1-aiodcounter06.cloudfunctions.net/api",
    "token": "c7979e050518223bedea817d510ac48819b98a9b90efc633ed586da956534ea1",
    "site_id": "global-innovation-anaheim-001",
    "org_id": "global-innovation"
}
```

### Step 3: Run Handshake Test

```bash
# On RPi
cd ~/aiodcounter01
python3 tests/test_handshake.py --token c7979e050518223bedea817d510ac48819b98a9b90efc633ed586da956534ea1 --test-data
```

### Step 4: Alternative - Manual Handshake

If the test script doesn't work, you can run the handshake manually:

```bash
# On RPi
cd ~/aiodcounter01
python3 -c "
from agents.handshake_agent import HandshakeAgent
agent = HandshakeAgent()
print('Current status:', agent.get_status())
result = agent.perform_handshake()
print('Handshake result:', result)
print('New status:', agent.get_status())
"
```

### Step 5: Verify Binding

After successful handshake, check the binding file:

```bash
cat config/binding.json
```

Expected output (approximately):
```json
{
    "bound": true,
    "camera_id": "CAM_xxxxxx",
    "site_id": "global-innovation-anaheim-001",
    "site_name": "Anaheim 001",
    "org_id": "global-innovation",
    "endpoint": "https://us-central1-aiodcounter06.cloudfunctions.net/ingestCounts",
    "auth_mode": "apikey",
    "auth_token": "device_HAILO-A001-xxxxx_xxxxx"
}
```

### Step 6: Verify in Firestore

Check the Firebase Console to verify:
1. `cameras` collection has a new document with the device serial
2. `site_tokens` document is marked as `used: true`

## Troubleshooting

### Token Invalid or Expired
```
Error: Invalid token
```
**Solution:** Generate a new token:
```bash
curl -X POST 'https://us-central1-aiodcounter06.cloudfunctions.net/api/dev/seed-token' \
  -H 'Content-Type: application/json' \
  -d '{"token":"YOUR_NEW_TOKEN","site_id":"global-innovation-anaheim-001","org_id":"global-innovation"}'
```

### Connection Error
```
Cannot reach backend
```
**Solution:** Check network connectivity:
```bash
curl -X GET 'https://us-central1-aiodcounter06.cloudfunctions.net/api/status'
```

### Already Bound
```
Device is already bound
```
**Solution:** Reset the device:
```bash
python3 -c "
from agents.handshake_agent import HandshakeAgent
agent = HandshakeAgent()
agent.reset()
print('Device reset!')
"
```

## API Endpoints Reference

### POST /api/device/register
Register a new device using QR token.

**Request:**
```json
{
    "serial": "HAILO-A001-xxxxxx",
    "token": "your_qr_token",
    "ip": "192.168.1.100",
    "firmware_version": "1.0.0"
}
```

**Response (Success):**
```json
{
    "success": true,
    "message": "Device registered and bound successfully",
    "binding": {
        "bound": true,
        "camera_id": "CAM_xxxxxx",
        "site_id": "global-innovation-anaheim-001",
        "endpoint": "https://...",
        ...
    }
}
```

### POST /api/device/activate
Confirm device activation.

**Request:**
```json
{
    "serial": "HAILO-A001-xxxxxx",
    "status": "active"
}
```

**Response:**
```json
{
    "success": true,
    "message": "Activation recorded"
}
```

## Files Created

| File | Purpose |
|------|---------|
| `backend/functions/src/agents/HandshakeAgent.js` | Backend handshake logic |
| `agents/handshake_agent.py` | RPi handshake agent |
| `tests/test_handshake.py` | Test script for handshake |
| `scripts/generate_token_cli.js` | Generate QR tokens |
| `config/qr_payload.json` | QR payload for testing |
