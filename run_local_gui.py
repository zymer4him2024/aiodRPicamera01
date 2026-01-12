import os
import sys
import json
import signal
from agents.orchestrator import Orchestrator

def main():
    print("--- Starting Standalone AI OD Camera (GUI Mode) ---")
    print("Note: If the background service is running, this might fail to access the camera.")
    print("Stop the service first: sudo systemctl stop aiod-counter")
    
    # Force visualization on
    config_path = "config/detection_config.json"
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
        config["visualize_local"] = True
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
    
    orch = Orchestrator()
    
    def signal_handler(sig, frame):
        print("\nStopping...")
        orch.stop_detection()
        sys.exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)
    
    orch.start_detection()
    
    print("\n[ACTIVE] Live window should now be visible on your RPi screen.")
    print("Press Ctrl+C in this terminal to exit.")
    
    # Keep main thread alive
    while True:
        import time
        time.sleep(1)

if __name__ == "__main__":
    main()
