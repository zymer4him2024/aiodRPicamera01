# Deployment Guide: Raspberry Pi 5 + Hailo-8 HAT+

## Prerequisites
1.  **Raspberry Pi 5** with Raspberry Pi OS (Bookworm 64-bit recommended).
2.  **Hailo-8 HAT+** installed and recognized by the system.
3.  **Hailo Software** installed (drivers and runtime).
    - Follow the official [Hailo Raspberry Pi Guide](https://github.com/hailo-ai/hailo-rpi5-examples) to install `hailo-all` and `hailo-tappas-core`.

## 1. Transfer Project Files
Copy the entire project directory to your Raspberry Pi. You can use `scp`:

```bash
scp -r /path/to/project user@raspberrypi_ip:/home/user/camera-system
```

## 2. Model Setup
Ensure the compiled model file exists.
- **Path**: `/home/digioptics_od/camera-system/models/yolov8n.hef`
- If you don't have it, download a pre-compiled YOLOv8n HEF from the Hailo Model Zoo or compile one using the Hailo Dataflow Compiler.
- Update `config/detection_config.json` if your model path is different.

## 3. Environment Setup
Run the included setup script to install dependencies and create a virtual environment.

```bash
cd camera-system
chmod +x scripts/setup_rpi.sh
./scripts/setup_rpi.sh
```

## 4. Configuration
1.  **Backend**: Edit `config/backend_config.json` with your Firebase API URL and Auth Token.
2.  **Camera**: Edit `config/camera_config.json` if you need to change resolution or device ID.

## 5. Verification
Run the verification script to check the Hailo hardware:

```bash
source venv/bin/activate
python3 tests/verify_hailo.py
```

## 6. Running the Application
Start the Detection API:

```bash
source venv/bin/activate
python3 main.py
```

The system will start listening on port 5000.

## 7. Local Monitoring Dashboard
Access the real-time monitoring dashboard by navigating to:
`http://<pi_ip>:5000/dashboard`

- **Live Feed**: Periodic snapshots from the camera.
- **Controls**: Start/Stop the detection loop manually.
- **Stats**: View uptime, camera status, and last report time.

## 8. Productionization: Auto-start
To set up the system to start automatically on boot:

1. Copy the service file:
   ```bash
   sudo cp scripts/aiod-counter.service /etc/systemd/system/
   ```
2. Reload systemd and enable the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable aiod-counter.service
   ```
3. Start the service:
   ```bash
   sudo systemctl start aiod-counter.service
   ```
4. View logs:
   ```bash
   journalctl -u aiod-counter.service -f
   ```
