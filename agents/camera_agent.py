import cv2
import json
import os
import time
import numpy as np
from utils.logger import get_logger

class CameraAgent:
    def __init__(self, config_path="config/camera_config.json"):
        self.logger = get_logger(self.__class__.__name__)
        self.config = self._load_config(config_path)
        self.cap = None
        self.is_running = False

    def _load_config(self, path):
        try:
            with open(path, 'r') as f:
                config = json.load(f)
                self.logger.info(f"Loaded camera config from {path}")
                return config
        except FileNotFoundError:
            self.logger.error(f"Config file not found: {path}")
            raise
        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON in config file: {path}")
            raise

    def start(self):
        """Initializes and starts the camera capture in a background thread."""
        if self.is_running:
            self.logger.warning("Camera is already running.")
            return

        import threading
        self.latest_frame = None
        self.frame_lock = threading.Lock()
        self.stop_event = threading.Event()

        device_id = self.config.get("device_id", 0)
        # resolution = self.config.get("resolution", [1920, 1080])
        # Use a more efficient resolution for faster transfers if needed, 
        # but keep high res for now as user didn't ask to lower it.
        
        self.logger.info(f"Opening camera device {device_id}...")
        self.cap = cv2.VideoCapture(device_id)

        if not self.cap.isOpened():
            self.logger.error(f"Failed to open camera device {device_id}")
            raise RuntimeError(f"Could not open camera device {device_id}")

        width, height = self.config.get("resolution", [640, 480]) # Default to 640x480 for Speed
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        # self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) # RPi specific optimization

        self.logger.info(f"Camera opened. Requested: {width}x{height}")
        self.is_running = True
        
        # Start capture thread
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()

    def _capture_loop(self):
        """Background loop for high-speed frame capture with auto-recovery."""
        self.logger.info("Starting background capture loop...")
        consecutive_failures = 0
        max_failures = 10
        
        while not self.stop_event.is_set():
            ret, frame = self.cap.read()
            if ret:
                consecutive_failures = 0
                with self.frame_lock:
                    self.latest_frame = frame
            else:
                consecutive_failures += 1
                self.logger.warning(f"Capture failure ({consecutive_failures}/{max_failures}).")
                
                if consecutive_failures >= max_failures:
                    self.logger.error("Too many capture failures. Attempting camera RECOVERY...")
                    self.cap.release()
                    time.sleep(2.0)
                    
                    device_id = self.config.get("device_id", 0)
                    self.cap = cv2.VideoCapture(device_id)
                    if self.cap.isOpened():
                        width, height = self.config.get("resolution", [640, 480])
                        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                        self.logger.info("Camera recovery SUCCESSFUL.")
                        consecutive_failures = 0
                    else:
                        self.logger.error("Camera recovery FAILED. Will retry...")
                
                time.sleep(0.1)

    def get_frame(self):
        """Returns the latest captured frame without blocking."""
        if not self.is_running:
            return None
        with self.frame_lock:
            return self.latest_frame

    def stop(self):
        """Releases the camera resources."""
        self.logger.info("Stopping camera...")
        self.is_running = False
        if hasattr(self, 'stop_event'):
            self.stop_event.set()
        if hasattr(self, 'capture_thread'):
            self.capture_thread.join(timeout=1.0)
        if self.cap and self.cap.isOpened():
            self.cap.release()
            self.logger.info("Camera resources released.")

    def __del__(self):
        self.stop()
