import subprocess
import re
from utils.logger import get_logger

class HardwareMonitor:
    """Monitors RPi and Hailo hardware metrics."""
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
    
    def get_cpu_temp(self):
        """Returns CPU temperature in Celsius."""
        try:
            result = subprocess.run(
                ['vcgencmd', 'measure_temp'],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                match = re.search(r'temp=(\d+\.\d+)', result.stdout)
                if match:
                    return float(match.group(1))
        except Exception as e:
            self.logger.error(f"Failed to read CPU temp: {e}")
        return None
    
    def get_hailo_temp(self):
        """Returns Hailo chip temperature in Celsius."""
        try:
            result = subprocess.run(
                ['hailortcli', 'fw-control', 'identify'],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                # Parse temperature from output
                match = re.search(r'Temperature:\s*(\d+\.?\d*)', result.stdout)
                if match:
                    return float(match.group(1))
        except Exception as e:
            self.logger.error(f"Failed to read Hailo temp: {e}")
        return None
    
    def get_hailo_load(self):
        """Returns Hailo utilization percentage."""
        try:
            result = subprocess.run(
                ['hailortcli', 'fw-control', 'identify'],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                # Parse utilization if available
                match = re.search(r'Utilization:\s*(\d+\.?\d*)%', result.stdout)
                if match:
                    return float(match.group(1))
        except Exception as e:
            self.logger.error(f"Failed to read Hailo load: {e}")
        return None
    
    def get_all_metrics(self):
        """Returns all hardware metrics as a dict."""
        return {
            "cpu_temp": self.get_cpu_temp(),
            "hailo_temp": self.get_hailo_temp(),
            "hailo_load": self.get_hailo_load()
        }
