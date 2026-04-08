import cv2
import numpy as np
import sys
import os
import threading
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config_loader import load_config
from utils.logger import setup_logger


class CameraAgent:
    """Handles USB camera capture with error handling and resource management."""

    def __init__(self, config_path):
        """Initialize camera agent with config.

        Args:
            config_path: Path to camera configuration JSON file
        """
        self.config = load_config(config_path)
        self.logger = setup_logger('CameraAgent', '/home/digioptics_od/camera-system/logs/camera.log')
        self.camera = None
        self.is_running = False
        self._lock = threading.Lock()  # Thread-safe frame access

        # Extract config values with defaults
        self.device_id = self.config.get('device_id', 0)
        self.resolution = tuple(self.config.get('resolution', [1920, 1080]))
        self.fps = self.config.get('fps', 30)
        self.flip_horizontal = self.config.get('flip_horizontal', False)
        self.flip_vertical = self.config.get('flip_vertical', False)

        self.logger.info(f"CameraAgent initialized with device_id={self.device_id}, "
                        f"resolution={self.resolution}, fps={self.fps}")

    def start(self):
        """Start camera with retry logic.

        Returns:
            bool: True if camera started successfully, False otherwise
        """
        max_retries = 3
        retry_delay = 2  # seconds

        for attempt in range(max_retries):
            try:
                self.logger.info(f"Starting camera (attempt {attempt + 1}/{max_retries})...")

                with self._lock:
                    # Open camera
                    self.camera = cv2.VideoCapture(self.device_id)

                    if not self.camera.isOpened():
                        raise Exception(f"Failed to open camera device {self.device_id}")

                    # Set resolution and FPS
                    self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
                    self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
                    self.camera.set(cv2.CAP_PROP_FPS, self.fps)

                    # Verify settings (actual values may differ from requested)
                    actual_width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
                    actual_height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    actual_fps = int(self.camera.get(cv2.CAP_PROP_FPS))

                    if actual_width != self.resolution[0] or actual_height != self.resolution[1]:
                        self.logger.warning(f"Requested resolution {self.resolution} not available, "
                                          f"using {actual_width}x{actual_height}")

                    self.logger.info(f"Camera started successfully: {actual_width}x{actual_height} @ {actual_fps}fps")
                    self.is_running = True
                    return True

            except Exception as e:
                self.logger.error(f"Camera start failed (attempt {attempt + 1}/{max_retries}): {e}")

                # Clean up on failure
                if self.camera:
                    try:
                        self.camera.release()
                    except Exception as release_error:
                        self.logger.error(f"Error releasing camera during cleanup: {release_error}")
                    finally:
                        self.camera = None

                # Retry logic
                if attempt < max_retries - 1:
                    self.logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    self.logger.error("All camera start attempts failed")
                    return False

        return False

    def get_frame(self):
        """Capture and return a single frame with thread-safe access.

        Returns:
            numpy.ndarray: BGR image frame, or None if capture failed
        """
        with self._lock:
            if not self.is_running or not self.camera or not self.camera.isOpened():
                self.logger.warning("Camera not active, cannot get frame")
                return None

            try:
                ret, frame = self.camera.read()

                if not ret or frame is None:
                    self.logger.warning("Failed to read frame from camera")
                    return None

                # Validate frame integrity
                if len(frame.shape) != 3:
                    self.logger.error(f"Invalid frame dimensions: expected 3D array, got shape {frame.shape}")
                    return None

                if frame.shape[2] != 3:
                    self.logger.error(f"Invalid frame channels: expected 3 (BGR), got {frame.shape[2]}")
                    return None

                # Validate frame is not empty
                if frame.shape[0] == 0 or frame.shape[1] == 0:
                    self.logger.error(f"Invalid frame size: {frame.shape[1]}x{frame.shape[0]}")
                    return None

                # Apply flips if configured
                if self.flip_horizontal:
                    frame = cv2.flip(frame, 1)
                if self.flip_vertical:
                    frame = cv2.flip(frame, 0)

                return frame

            except Exception as e:
                self.logger.error(f"Error reading frame: {e}")
                return None

    def stop(self):
        """Stop camera and release resources with proper cleanup."""
        self.logger.info("Stopping camera...")

        with self._lock:
            self.is_running = False

            if self.camera:
                try:
                    self.camera.release()
                    self.logger.info("Camera released successfully")
                except Exception as e:
                    self.logger.error(f"Error releasing camera: {e}")
                finally:
                    self.camera = None
            else:
                self.logger.info("Camera already released or not initialized")

    def is_active(self):
        """Check if camera is active and ready.

        Returns:
            bool: True if camera is running and available, False otherwise
        """
        with self._lock:
            return self.is_running and self.camera is not None and self.camera.isOpened()

    def __del__(self):
        """Destructor to ensure camera resources are released."""
        if hasattr(self, 'is_running') and self.is_running:
            self.stop()
