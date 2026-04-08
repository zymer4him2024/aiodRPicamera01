import sys
import time
import os

print("--- STARTUP DOCTOR (V31 Diagnostic) ---")

# 1. Test Imports
print("1. Testing Imports...")
try:
    from utils.binding_manager import BindingManager
    from agents.transport_agent import TransportAgent
    from agents.orchestrator import Orchestrator
    print("   [OK] Imports successful.")
except Exception as e:
    print(f"   [FAIL] Import failed: {e}")
    sys.exit(1)

# 2. Test Hardware Detection
print("2. Testing Hardware...")
try:
    from agents.camera_agent import CameraAgent
    cam = CameraAgent()
    print("   [OK] Camera Agent initialized.")
    
    from agents.inference_agent_hailo import InferenceAgent
    inf = InferenceAgent()
    print("   [OK] Inference Agent initialized.")
except Exception as e:
    print(f"   [FAIL] Hardware init failed: {e}")
    print("   Check if another process is using the camera or Hailo (pkill -9 python3).")

# 3. Test Binding Manager
print("3. Testing Binding Logic...")
try:
    bm = BindingManager()
    info = bm.get_info()
    print(f"   [OK] Serial: {info['serial']}")
    print(f"   [OK] Bound: {info['bound']}")
except Exception as e:
    print(f"   [FAIL] Binding Manager error: {e}")

# 4. Test API Port
print("4. Checking Port 5000...")
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.bind(("0.0.0.0", 5000))
    s.close()
    print("   [OK] Port 5000 is available.")
except Exception as e:
    print(f"   [FAIL] Port 5000 is BUSY. Kill existing main.py: {e}")

print("\n--- DIAGNOSTIC COMPLETE ---")
print("If all OK, run: DISPLAY=:0 python3 main.py")
