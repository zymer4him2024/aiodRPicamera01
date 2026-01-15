import signal
import sys
import time
from api.detection_api import app, get_orchestrator
from utils.logger import get_logger

logger = get_logger("Main")

def signal_handler(sig, frame):
    logger.info("Shutdown signal received. Cleaning up...")
    orch = get_orchestrator()
    if orch:
        orch.stop_detection()
    logger.info("System exited gracefully.")
    sys.exit(0)

def main():
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("Starting AI Object Detection System...")
    
    # 1. Start Flask API in a background thread
    # host 0.0.0.0 is required for RPi to be accessible over network
    import threading
    flask_thread = threading.Thread(
        target=lambda: app.run(host='0.0.0.0', port=5000, threaded=True, use_reloader=False),
        daemon=True
    )
    logger.info("Starting Flask API thread on port 5000...")
    flask_thread.start()

    # 2. Wait a moment for Flask to bind
    time.sleep(1)

    # Start Remote Command Listener
    from utils.command_listener import CommandListener
    from utils.binding_manager import BindingManager
    binding = BindingManager()
    if binding.is_bound():
        CommandListener(binding.serial_number).start()
        logger.info("Remote control enabled")
    else:
        logger.warning("Device not bound - remote control disabled")

    # 3. Initialize and START orchestrator (Blocks on main thread for GUI)
    orch = get_orchestrator()
    if orch:
        logger.info("Starting detection loop on main thread...")
        orch.start_detection()
    else:
        logger.error("Failed to initialize Orchestrator.")

if __name__ == "__main__":
    main()
