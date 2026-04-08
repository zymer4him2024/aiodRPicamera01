#!/usr/bin/env python3
"""
Orchestrator Agent - Coordinates all sub-agents for fully automated operation.

Architecture:
- Camera Agent (captures frames)
- Inference Agent (Hailo-8 detection)
- Counting Agent (processes detections)
- Transport Agent (sends to Firebase)

Features:
- Automatic agent lifecycle management
- Health monitoring and auto-restart
- Graceful error handling
- Performance metrics
- Configurable report intervals
"""

import time
import threading
import queue
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.camera_agent import CameraAgent
from agents.inference_agent_hailo import InferenceAgentHailo
from agents.counting_agent import CountingAgent
from agents.transport_agent import TransportAgent
from utils.logger import setup_logger


class OrchestratorAgent:
    """Orchestrates all detection agents in a fully automated pipeline."""

    def __init__(self, config_dir='/home/digioptics_od/camera-system/config'):
        """Initialize orchestrator with configuration directory.

        Args:
            config_dir: Path to configuration directory containing all config files
        """
        self.config_dir = config_dir
        self.logger = setup_logger('Orchestrator', '/home/digioptics_od/camera-system/logs/orchestrator.log')

        # Agent instances
        self.camera = None
        self.inference = None
        self.counting = None
        self.transport = None

        # Control flags
        self.running = False
        self.paused = False

        # Threading
        self.detection_thread = None
        self.reporting_thread = None
        self.health_monitor_thread = None

        # Queues for inter-agent communication
        self.frame_queue = queue.Queue(maxsize=10)
        self.detection_queue = queue.Queue(maxsize=100)

        # Metrics
        self.metrics = {
            'frames_processed': 0,
            'detections_count': 0,
            'reports_sent': 0,
            'errors': 0,
            'start_time': None,
            'last_report_time': None
        }

        # Configuration
        self.report_interval = 15  # seconds (loaded from backend_config)

        self.logger.info("Orchestrator initialized")

    def initialize_agents(self):
        """Initialize all sub-agents.

        Returns:
            bool: True if all agents initialized successfully
        """
        try:
            self.logger.info("Initializing sub-agents...")

            # Camera Agent
            camera_config = os.path.join(self.config_dir, 'camera_config.json')
            self.camera = CameraAgent(camera_config)
            self.logger.info("✓ Camera agent initialized")

            # Inference Agent (Hailo-8)
            detection_config = os.path.join(self.config_dir, 'detection_config.json')
            self.inference = InferenceAgentHailo(detection_config)
            self.logger.info("✓ Inference agent initialized")

            # Counting Agent
            counting_config = os.path.join(self.config_dir, 'counting_config.json')
            self.counting = CountingAgent(counting_config)
            self.logger.info("✓ Counting agent initialized")

            # Transport Agent
            backend_config = os.path.join(self.config_dir, 'backend_config.json')
            self.transport = TransportAgent(backend_config)
            self.logger.info("✓ Transport agent initialized")

            # Load report interval from backend config
            import json
            with open(backend_config, 'r') as f:
                config = json.load(f)
                self.report_interval = config.get('report_interval', 15)

            self.logger.info(f"Report interval: {self.report_interval} seconds")

            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize agents: {e}")
            return False

    def start(self):
        """Start the orchestrator and all sub-agents.

        Returns:
            bool: True if started successfully
        """
        if self.running:
            self.logger.warning("Orchestrator already running")
            return False

        try:
            self.logger.info("="*60)
            self.logger.info("Starting Camera Detection System")
            self.logger.info("="*60)

            # Initialize agents if not already done
            if self.camera is None:
                if not self.initialize_agents():
                    return False

            # Start camera
            self.logger.info("Starting camera...")
            if not self.camera.start():
                self.logger.error("Failed to start camera")
                return False
            self.logger.info("✓ Camera started")

            # Load inference model
            self.logger.info("Loading Hailo-8 model...")
            if not self.inference.load_model():
                self.logger.error("Failed to load inference model")
                self.camera.stop()
                return False
            self.logger.info("✓ Hailo-8 model loaded")

            # Send activation signal to Firebase
            self.logger.info("Sending activation signal...")
            self.transport.send_activation()

            # Start processing threads
            self.running = True
            self.metrics['start_time'] = time.time()

            self.detection_thread = threading.Thread(target=self._detection_loop, daemon=True)
            self.detection_thread.start()
            self.logger.info("✓ Detection thread started")

            self.reporting_thread = threading.Thread(target=self._reporting_loop, daemon=True)
            self.reporting_thread.start()
            self.logger.info("✓ Reporting thread started")

            self.health_monitor_thread = threading.Thread(target=self._health_monitor_loop, daemon=True)
            self.health_monitor_thread.start()
            self.logger.info("✓ Health monitor started")

            self.logger.info("="*60)
            self.logger.info("✓ System fully operational")
            self.logger.info("="*60)

            # Send initial status
            self.transport.send_status("active")

            return True

        except Exception as e:
            self.logger.error(f"Failed to start orchestrator: {e}")
            self.stop()
            return False

    def _detection_loop(self):
        """Main detection loop - runs continuously."""
        self.logger.info("Detection loop started")

        while self.running:
            try:
                if self.paused:
                    time.sleep(0.1)
                    continue

                # Get frame from camera
                frame = self.camera.get_frame()

                if frame is None:
                    self.logger.warning("No frame from camera")
                    time.sleep(0.1)
                    continue

                # Run inference
                start_time = time.time()
                detections = self.inference.detect(frame)
                inference_time = (time.time() - start_time) * 1000  # ms

                # Update metrics
                self.metrics['frames_processed'] += 1

                if detections:
                    self.metrics['detections_count'] += len(detections)

                    # Log inference performance periodically
                    if self.metrics['frames_processed'] % 100 == 0:
                        fps = 1000 / inference_time
                        self.logger.info(f"Performance: {inference_time:.1f}ms/frame, "
                                       f"{fps:.1f} FPS, {len(detections)} objects")

                # Add detections to queue for reporting
                self.detection_queue.put({
                    'detections': detections,
                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'inference_time': inference_time
                })

                # Small delay to prevent CPU spinning
                time.sleep(0.01)

            except Exception as e:
                self.logger.error(f"Error in detection loop: {e}")
                self.metrics['errors'] += 1
                time.sleep(1)  # Back off on error

    def _reporting_loop(self):
        """Reporting loop - aggregates and sends counts to Firebase."""
        self.logger.info("Reporting loop started")

        accumulated_detections = []

        while self.running:
            try:
                # Collect detections for report_interval seconds
                timeout = time.time() + self.report_interval

                while time.time() < timeout and self.running:
                    try:
                        # Get detection with short timeout to check running flag
                        detection_data = self.detection_queue.get(timeout=1.0)
                        accumulated_detections.extend(detection_data['detections'])
                    except queue.Empty:
                        continue

                if not self.running:
                    break

                # Process accumulated detections
                if accumulated_detections:
                    counts = self.counting.process_detections(accumulated_detections)

                    # Send to Firebase
                    if self.transport.send_counts(counts):
                        self.metrics['reports_sent'] += 1
                        self.metrics['last_report_time'] = time.time()
                        self.logger.info(f"Report sent: {counts}")
                    else:
                        self.logger.warning("Failed to send report to Firebase")

                    # Clear accumulated detections
                    accumulated_detections = []
                else:
                    # Send zero counts if no detections
                    empty_counts = {
                        'total': 0,
                        'timestamp': datetime.utcnow().isoformat() + 'Z'
                    }
                    self.transport.send_counts(empty_counts)
                    self.logger.debug("No detections in interval, sent zero counts")

            except Exception as e:
                self.logger.error(f"Error in reporting loop: {e}")
                self.metrics['errors'] += 1
                time.sleep(5)

    def _health_monitor_loop(self):
        """Health monitoring loop - checks agent status and restarts if needed."""
        self.logger.info("Health monitor started")

        check_interval = 30  # seconds

        while self.running:
            try:
                time.sleep(check_interval)

                if not self.running:
                    break

                # Check camera health
                if not self.camera or not hasattr(self.camera, 'cap') or self.camera.cap is None:
                    self.logger.error("Camera agent unhealthy - attempting restart")
                    self._restart_camera()

                # Check inference health
                if not self.inference or not self.inference.is_ready():
                    self.logger.error("Inference agent unhealthy - attempting restart")
                    self._restart_inference()

                # Log uptime and metrics
                uptime = time.time() - self.metrics['start_time']
                uptime_hours = uptime / 3600

                self.logger.info(f"Health check - Uptime: {uptime_hours:.2f}h, "
                               f"Frames: {self.metrics['frames_processed']}, "
                               f"Reports: {self.metrics['reports_sent']}, "
                               f"Errors: {self.metrics['errors']}")

                # Send periodic status update
                self.transport.send_status("active")

            except Exception as e:
                self.logger.error(f"Error in health monitor: {e}")

    def _restart_camera(self):
        """Attempt to restart camera agent."""
        try:
            self.logger.info("Restarting camera agent...")

            if self.camera:
                self.camera.stop()

            time.sleep(2)

            if self.camera.start():
                self.logger.info("✓ Camera agent restarted")
            else:
                self.logger.error("Failed to restart camera agent")

        except Exception as e:
            self.logger.error(f"Error restarting camera: {e}")

    def _restart_inference(self):
        """Attempt to restart inference agent."""
        try:
            self.logger.info("Restarting inference agent...")

            if self.inference:
                self.inference.unload_model()

            time.sleep(2)

            if self.inference.load_model():
                self.logger.info("✓ Inference agent restarted")
            else:
                self.logger.error("Failed to restart inference agent")

        except Exception as e:
            self.logger.error(f"Error restarting inference: {e}")

    def stop(self):
        """Stop the orchestrator and all sub-agents."""
        self.logger.info("Stopping orchestrator...")

        self.running = False

        # Wait for threads to finish
        if self.detection_thread and self.detection_thread.is_alive():
            self.detection_thread.join(timeout=5)

        if self.reporting_thread and self.reporting_thread.is_alive():
            self.reporting_thread.join(timeout=5)

        if self.health_monitor_thread and self.health_monitor_thread.is_alive():
            self.health_monitor_thread.join(timeout=5)

        # Stop agents
        if self.inference:
            self.inference.unload_model()
            self.logger.info("✓ Inference agent stopped")

        if self.camera:
            self.camera.stop()
            self.logger.info("✓ Camera agent stopped")

        # Send final status
        if self.transport:
            self.transport.send_status("inactive")

        # Log final metrics
        if self.metrics['start_time']:
            uptime = time.time() - self.metrics['start_time']
            self.logger.info(f"Final metrics - Uptime: {uptime:.1f}s, "
                           f"Frames: {self.metrics['frames_processed']}, "
                           f"Reports: {self.metrics['reports_sent']}, "
                           f"Errors: {self.metrics['errors']}")

        self.logger.info("Orchestrator stopped")

    def pause(self):
        """Pause detection (camera keeps running)."""
        self.paused = True
        self.logger.info("Detection paused")

    def resume(self):
        """Resume detection."""
        self.paused = False
        self.logger.info("Detection resumed")

    def get_status(self):
        """Get current orchestrator status.

        Returns:
            dict: Status information
        """
        uptime = time.time() - self.metrics['start_time'] if self.metrics['start_time'] else 0

        return {
            'running': self.running,
            'paused': self.paused,
            'uptime_seconds': uptime,
            'metrics': self.metrics.copy(),
            'agents': {
                'camera': self.camera is not None and hasattr(self.camera, 'cap') and self.camera.cap is not None,
                'inference': self.inference is not None and self.inference.is_ready(),
                'counting': self.counting is not None,
                'transport': self.transport is not None
            }
        }


if __name__ == "__main__":
    # Simple test
    orchestrator = OrchestratorAgent()

    try:
        if orchestrator.start():
            print("Orchestrator started successfully")
            print("Press Ctrl+C to stop")

            while True:
                time.sleep(10)
                status = orchestrator.get_status()
                print(f"\nStatus: {status['metrics']}")
        else:
            print("Failed to start orchestrator")

    except KeyboardInterrupt:
        print("\nStopping...")
        orchestrator.stop()
        print("Stopped")
