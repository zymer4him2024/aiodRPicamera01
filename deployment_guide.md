# Production Handbook: AI OD Camera "Master Image"

This guide explains how to manage, capture, and duplicate your **Master SD Image** for the RPi 5 + Hailo-8 hardware units.

## 1. The "Master Image" Concept
Your current SD card is now a **Master Image**. 
- **Production Ready**: It starts in a "factory-fresh" UNBOUND state.
- **Self-Healing**: It automatically recovers from camera or AI hangs.
- **Dynamic Identity**: It generates a unique hardware serial number on boot.

---

## 2. Capturing the "Golden Image" (Mass Production)
To create 100 cameras, you capture this one card and clone it.

### Step A: Sanitization (On the RPi)
This removes your personal logs and history while keeping the code.
```bash
# Run this once on your finished RPi
curl -s http://192.168.0.90:8000/prepare_master.sh | bash
sudo shutdown -h now
```

### Step B: Clone the Card (On your Mac)
1. Plug the SD card into your Mac.
2. Open terminal and run `diskutil list` to find the SD card (e.g., `disk4`).
3. Save the image to your Desktop:
   ```bash
   # Replace rdiskN with your actual number (e.g., rdisk4)
   sudo dd if=/dev/rdiskN of=~/Desktop/aiod_master_v1.0.img bs=1m status=progress
   ```
   **The file `aiod_master_v1.0.img` will appear on your Mac Desktop after this finishing.**

---

## 3. Deploying to New Units
Use **Raspberry Pi Imager** on your Mac to flash the `.img` file to new SD cards.

1. **Plug & Play**: Insert the new card into a fresh RPi.
2. **Auto-Start**: The system will boot and start detection locally.
3. **Verify Identity**:
   ```bash
   curl http://<new_pi_ip>:5000/api/info
   ```
   *(It will have a different serial number than the first one!)*

---

## 4. The Universal Handshake (API)
The camera works with **any** backend (Firebase, AWS, Custom Python/Node) by adapting its headers and auth mode.

### Example: Custom AWS/GCP Backend
If your backend requires a custom API Key and a specialized "Device-Mode" header:

```bash
curl -X POST http://<camera_ip>:5000/api/bind \
     -H "Content-Type: application/json" \
     -d '{
       "endpoint": "https://api.yourcloud.com/v1/ingest",
       "auth_mode": "custom",
       "custom_auth_header": "X-Device-Token",
       "auth_token": "SUPER_SECRET_TOKEN",
       "custom_headers": {
         "X-Device-Mode": "production",
         "X-Tenant-ID": "TENANT_123"
       },
       "camera_id": "MAIN_GATE_01",
       "site_id": "WAREHOUSE_A"
     }'
```

---

## 5. Testing Connectivity
Before leaving the installation site, verify the camera can actually "talk" to the backend:

```bash
curl http://<camera_ip>:5000/api/ping
```
*(Returns `{"success": true}` if the backend confirms receipt of the handshake)*

## 6. Supported Auth & Payload Modes
The camera can adapt its identity schema to match your backend exactly.

| Feature | Option | Value / Header |
| :--- | :--- | :--- |
| **Auth** | `bearer` | `Authorization: Bearer <token>` |
| **Auth** | `apikey` | `X-API-Key: <token>` |
| **Auth** | `custom` | `<custom_auth_header>: <token>` |
| **Payload** | `legacy` | **Flat Structure** (Standard for your current dashboard) |
| **Payload** | `universal`| **Nested Structure** (Serial# + Uptime + Counts) |

---

### Example: Existing Firebase Dashboard (Legacy)
To bind the unit so it works perfectly with your current React dashboard:

```bash
curl -X POST http://<camera_ip>:5000/api/bind \
     -H "Content-Type: application/json" \
     -d '{
       "endpoint": "https://your-firebase-url.com/ingest",
       "auth_token": "YOUR_LEGACY_KEY",
       "payload_format": "legacy",
       "camera_id": "RETAIL_001",
       "site_id": "NORTH_GATE"
     }'
```
