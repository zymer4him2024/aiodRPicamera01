import os
import sys
import time
import subprocess
from utils.logger import get_logger
from utils.binding_manager import BindingManager
from utils.network_manager import NetworkManager

# Configuration
HOTSPOT_SSID = "AIOD-Installer"
HOTSPOT_PASS = "aiod1234"
INTERNET_CHECK_RETRIES = 5
INTERNET_CHECK_DELAY = 5

logger = get_logger("StartupManager")
binding_manager = BindingManager()
network_manager = NetworkManager()

def launch_script(script_path):
    """Launches a python script and waits for it."""
    try:
        logger.info(f"Launching {script_path}...")
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'
        
        # Using sys.executable to ensure same python interpreter
        process = subprocess.run(
            [sys.executable, script_path],
            check=False, # Don't raise exception on non-zero exit, just return
            env=env
        )
        return process.returncode
    except Exception as e:
        logger.error(f"Failed to launch {script_path}: {e}")
        return 1

def ensure_hotspot():
    """Ensures Hotspot is active."""
    logger.info("Ensuring Hotspot is active...")
    if not network_manager.create_hotspot(HOTSPOT_SSID, HOTSPOT_PASS):
        logger.error("Failed to create hotspot!")

def check_connection():
    """Checks internet connection with retries."""
    logger.info("Verifying internet connection...")
    for i in range(INTERNET_CHECK_RETRIES):
        if network_manager.check_internet():
            logger.info("Internet connection verified.")
            return True
        logger.warning(f"No internet ({i+1}/{INTERNET_CHECK_RETRIES}). Retrying in {INTERNET_CHECK_DELAY}s...")
        time.sleep(INTERNET_CHECK_DELAY)
    return False

def main():
    logger.info("=== RPi Startup Manager ===")
    
    # Check Binding State
    is_bound = binding_manager.is_bound()
    logger.info(f"Device Bound State: {is_bound}")
    
    if not is_bound:
        logger.info("Mode: ONBOARDING (Unbound)")
        ensure_hotspot()
        script = "onboarding/onboarding_server.py"
    else:
        logger.info("Mode: PRODUCTION (Bound)")
        # Check Internet
        if check_connection():
            logger.info("Network OK. Starting Orchestrator.")
            script = "agents/orchestrator.py"
        else:
            logger.warning("Network FAILED. Falling back to ONBOARDING mode for reconfiguration.")
            ensure_hotspot()
            script = "onboarding/onboarding_server.py"

    # Launch selected script
    # We exit after the script exits, allowing systemd to restart us and re-evaluate state.
    # This handles the case where Onboarding creates a binding and exits/crashes -> restart -> now Bound -> Orchestrator.
    full_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), script)
    exit_code = launch_script(full_path)
    
    logger.info(f"Subprocess finished with code {exit_code}. Exiting Startup Manager.")
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
