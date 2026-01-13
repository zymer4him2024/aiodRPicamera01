import json
import os
import subprocess
from utils.logger import get_logger

class BindingManager:
    """Manages the production binding state and hardware identity."""
    
    def __init__(self, binding_path="config/binding.json"):
        self.logger = get_logger(self.__class__.__name__)
        self.binding_path = binding_path
        self.config = self._load_binding()
        self.serial_number = self._generate_serial()

    def _load_binding(self):
        if os.path.exists(self.binding_path):
            try:
                with open(self.binding_path, 'r') as f:
                    data = json.load(f)
                    self.logger.info(f"Loaded binding from {self.binding_path}")
                    return data
            except Exception as e:
                self.logger.error(f"Failed to read binding file: {e}")
        
        self.logger.info("No binding found. Standing by in UNBOUND mode.")
        return {"bound": False}

    def _generate_serial(self):
        """Generates Serial: HAILO-{SLC}-{RPI_SERIAL}"""
        try:
            # Get RPi Serial
            cpuserial = "0000000000000000"
            if os.path.exists('/proc/cpuinfo'):
                with open('/proc/cpuinfo', 'r') as f:
                    for line in f:
                        if line.startswith('Serial'):
                            cpuserial = line.split(':')[1].strip()
            
            slc = "A001" # Default SLC, could be configured
            return f"HAILO-{slc}-{cpuserial}"
        except Exception as e:
            self.logger.error(f"Failed to generate serial: {e}")
            return "HAILO-UNKNOWN"

    def is_bound(self):
        return self.config.get("bound", False)

    def bind(self, config_data):
        """Stores new binding configuration."""
        try:
            config_data["bound"] = True
            with open(self.binding_path, 'w') as f:
                json.dump(config_data, f, indent=4)
            self.config = config_data
            self.logger.info("Hardware BOUND successfully.")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save binding: {e}")
            return False

    def unbind(self):
        """Resets to UNBOUND mode."""
        try:
            if os.path.exists(self.binding_path):
                os.remove(self.binding_path)
            self.config = {"bound": False}
            self.logger.info("Hardware UNBOUND (Factory Reset).")
            return True
        except Exception as e:
            self.logger.error(f"Failed to unbind: {e}")
            return False

    def get_info(self):
        return {
            "serial": self.serial_number,
            "bound": self.is_bound(),
            "camera_id": self.config.get("camera_id", "N/A"),
            "site_id": self.config.get("site_id", "N/A"),
            "endpoint": self.config.get("endpoint", "N/A")
        }
