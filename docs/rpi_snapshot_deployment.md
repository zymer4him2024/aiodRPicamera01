# RPi Deployment Guide - Superadmin Remote Control

## Overview
This guide will help you deploy the snapshot capture and remote control updates to your Raspberry Pi.

## Files to Update

### 1. Command Listener (`utils/command_listener.py`)
**Location:** `~/camera-system/utils/command_listener.py`

**Changes:**
- Added snapshot command handling
- Integrated Firebase Storage upload
- Added metadata creation in Firestore

### 2. Detection API (`api/detection_api.py`)
**Location:** `~/camera-system/api/detection_api.py`

**Changes:**
- Added `/snapshot` endpoint to capture current frame

---

## Deployment Steps

### Option A: Manual Copy (Recommended if SSH is working)

From your **local machine**, run:

```bash
cd /Users/shawnshlee/1_Antigravity/1_Antig_aiodcounter01

# Find your RPi's IP address first
# Then copy the files
scp utils/command_listener.py digioptics_od@YOUR_RPI_IP:/home/digioptics_od/camera-system/utils/
scp api/detection_api.py digioptics_od@YOUR_RPI_IP:/home/digioptics_od/camera-system/api/

# Restart the service
ssh digioptics_od@YOUR_RPI_IP "sudo systemctl restart aiod-counter"
```

### Option B: Manual Update (If SSH is not working)

SSH into your RPi and run these commands:

#### 1. Update Command Listener

```bash
cd ~/camera-system
cat << 'EOF' > utils/command_listener.py
# Paste the entire content from:
# /Users/shawnshlee/1_Antigravity/1_Antig_aiodcounter01/utils/command_listener.py
EOF
```

#### 2. Update Detection API

Add the snapshot endpoint to `api/detection_api.py` after the `/api/detection/stop` route:

```python
@app.route('/snapshot', methods=['POST'])
def capture_snapshot():
    """Capture and return the latest annotated frame as JPEG"""
    orch = get_orchestrator()
    if not orch:
        return jsonify({"error": "Orchestrator not initialized"}), 500
    
    try:
        import cv2
        
        # Get the latest annotated frame
        frame = orch.last_annotated_frame
        if frame is None:
            return jsonify({"error": "No frame available"}), 404
        
        # Encode as JPEG with 85% quality
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 85]
        success, buffer = cv2.imencode('.jpg', frame, encode_param)
        
        if not success:
            return jsonify({"error": "Failed to encode frame"}), 500
        
        # Return as binary image
        response = make_response(buffer.tobytes())
        response.headers['Content-Type'] = 'image/jpeg'
        response.headers['Content-Disposition'] = 'inline; filename=snapshot.jpg'
        return response
        
    except Exception as e:
        logger.error(f"Error capturing snapshot: {e}")
        return jsonify({"error": str(e)}), 500
```

#### 3. Restart the Service

```bash
sudo systemctl restart aiod-counter
```

#### 4. Verify Installation

```bash
# Check logs for successful startup
journalctl -u aiod-counter -f | grep -i "command\|snapshot"
```

You should see:
- `Remote Command Listener started`
- No errors related to imports or Firebase

---

## Testing the Installation

### Test 1: Verify Command Listener is Running

```bash
journalctl -u aiod-counter -n 50 | grep "Remote"
```

Expected output:
```
Remote Command Listener started
```

### Test 2: Test Snapshot Endpoint Locally

```bash
curl -X POST http://localhost:5000/snapshot --output test_snapshot.jpg
```

Expected: A JPEG file is created with the current camera view

### Test 3: Test from Dashboard

1. Log in as superadmin
2. Go to Hardware Fleet
3. Click the camera icon button on any online camera
4. Wait 3-5 seconds
5. Check Firebase Storage console for new snapshot

---

## Troubleshooting

### Error: "No module named 'google.cloud.storage'"

**Solution:**
```bash
pip3 install google-cloud-storage
```

### Error: "No frame available"

**Cause:** Detection is not running

**Solution:**
```bash
curl -X POST http://localhost:5000/start
```

### Error: Permission denied when uploading to Storage

**Cause:** Firebase credentials not configured

**Solution:**
```bash
# Verify credentials exist
ls -la ~/camera-system/config/firebase-credentials.json

# If missing, re-download from Firebase Console
```

### Snapshot command not executing

**Check:**
1. Firestore rules deployed: `firebase deploy --only firestore:rules`
2. User is logged in as superadmin
3. Command appears in Firestore `commands` collection with `status: 'pending'`
4. RPi logs show command detection: `journalctl -u aiod-counter -f | grep snapshot`

---

## Verification Checklist

- [ ] Command listener starts without errors
- [ ] `/snapshot` endpoint returns JPEG image
- [ ] Snapshot button appears in dashboard (superadmin only)
- [ ] Clicking snapshot button creates command in Firestore
- [ ] RPi detects and executes snapshot command
- [ ] Snapshot appears in Firebase Storage
- [ ] Snapshot metadata appears in Firestore `snapshots` collection

---

## File Locations Reference

**Local Machine:**
- Command Listener: `/Users/shawnshlee/1_Antigravity/1_Antig_aiodcounter01/utils/command_listener.py`
- Detection API: `/Users/shawnshlee/1_Antigravity/1_Antig_aiodcounter01/api/detection_api.py`

**Raspberry Pi:**
- Command Listener: `/home/digioptics_od/camera-system/utils/command_listener.py`
- Detection API: `/home/digioptics_od/camera-system/api/detection_api.py`
- Service: `/etc/systemd/system/aiod-counter.service`
- Logs: `journalctl -u aiod-counter`
