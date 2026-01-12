import time
import threading
import traceback
import numpy as np
import cv2
from utils.logger import get_logger
from agents.camera_agent import CameraAgent
from agents.inference_agent_hailo import InferenceAgent
from agents.counting_agent import CountingAgent
from agents.transport_agent import TransportAgent

class Orchestrator:
    def __init__(self, report_interval=5.0):
        self.logger = get_logger(self.__class__.__name__)
        self.report_interval = report_interval
        self.running = False
        self.thread = None
        self.start_time = None
        self.last_report_time_str = "N/A"
        self.latest_counts = {}
        self.fps = 0.0
        self.last_annotated_frame = None

        self.logger.info("Initializing Orchestrator and agents...")
        try:
            self.camera = CameraAgent()
            self.inference = InferenceAgent()
            self.counter = CountingAgent()
            self.transport = TransportAgent()
        except Exception as e:
            self.logger.error(f"Failed to initialize agents: {e}")
            raise

    def start_detection(self):
        """
        Starts the dual-threaded detection pipeline.
        """
        if self.running:
            self.logger.warning("Detection pipeline already running.")
            return

        self.logger.info("Starting optimized 20 FPS detection pipeline...")
        try:
            self.camera.start()
            self.inference.start()
            
            self.transport.send_activation({
                "status": "active",
                "activated_at": time.time()
            })
            
            self.running = True
            self.start_time = time.time()
            self.latest_detections = []
            self.detections_lock = threading.Lock()
            
            # 1. Start Inference Thread (Background)
            self.inference_thread = threading.Thread(target=self._inference_loop, daemon=True)
            self.inference_thread.start()
            
            # 2. Start Display Loop (Main/Current Thread)
            # This allows cv2.imshow to run on the main thread if needed
            self._display_loop()
            
        except Exception as e:
            self.logger.error(f"Failed to start optimized pipeline: {e}")
            self.stop_detection()

    def _inference_loop(self):
        """Background thread for high-speed Hailo inference with FPS throttling."""
        self.logger.info("Inference thread started.")
        target_fps = self.inference.config.get("target_fps", 10)
        cycle_time = 1.0 / target_fps if target_fps > 0 else 0
        
        while self.running:
            loop_start = time.time()
            try:
                frame = self.camera.get_frame()
                if frame is None:
                    time.sleep(0.005)
                    continue

                # Run Inference
                detections = self.inference.run_inference(frame)
                
                with self.detections_lock:
                    self.latest_detections = detections
                
                # Update counts for dashboard
                counts = self.counter.count_objects(detections)
                for cls in ["Pedestrians", "Cars", "Buses", "Trucks", "Motorcycles"]:
                    self.latest_counts[cls] = counts.get(cls, 0)
                self.latest_counts["total"] = counts.get("total", 0)
                
                # Report at interval
                current_time = time.time()
                if not hasattr(self, 'last_report_time'): self.last_report_time = 0
                if current_time - self.last_report_time >= self.report_interval:
                    threading.Thread(target=self.transport.send_counts, args=(counts,), daemon=True).start()
                    self.last_report_time_str = time.strftime("%Y-%m-%d %H:%M:%S")
                    self.last_report_time = current_time

                # Throttle
                elapsed = time.time() - loop_start
                if elapsed < cycle_time:
                    time.sleep(cycle_time - elapsed)

            except Exception as e:
                self.logger.error(f"Inference Thread Error: {e}")
                time.sleep(0.1)

    def _display_loop(self):
        """Main loop for visualization with FPS throttling."""
        self.logger.info("Display loop started.")
        target_fps = self.inference.config.get("target_fps", 10)
        cycle_time = 1.0 / target_fps if target_fps > 0 else 0
        
        frame_count = 0
        fps_start_time = time.time()

        while self.running:
            now = time.time() # Define 'now' here for the whole cycle
            loop_start = now
            try:
                frame = self.camera.get_frame()
                if frame is None:
                    time.sleep(0.01)
                    continue

                with self.detections_lock:
                    current_detections = self.latest_detections.copy()

                # Annotate
                annotated_img = self._annotate_frame(frame, current_detections)

                # Local GUI
                if self.inference.config.get("visualize_local", True):
                    cv2.imshow("Hailo AI Object Detection (Throttled)", annotated_img)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        self.stop_detection()
                        break

                # Watchdog: Is the inference thread alive?
                if not hasattr(self, '_last_watchdog_check'): self._last_watchdog_check = 0
                if now - self._last_watchdog_check >= 5.0:
                    if not self.inference_thread.is_alive():
                        self.logger.error("WATCHDOG: Inference thread died! Attempting restart...")
                        self.inference_thread = threading.Thread(target=self._inference_loop, daemon=True)
                        self.inference_thread.start()
                    self._last_watchdog_check = now

                # FPS Calculation
                frame_count += 1
                elapsed_total = now - fps_start_time
                if elapsed_total >= 1.0:
                    self.fps = frame_count / elapsed_total
                    self.latest_counts["fps"] = round(self.fps, 2)
                    self.latest_counts["last_update"] = time.strftime("%H:%M:%S")
                    frame_count = 0
                    fps_start_time = now

                # Throttle
                elapsed_loop = time.time() - loop_start
                if elapsed_loop < cycle_time:
                    time.sleep(cycle_time - elapsed_loop)

            except Exception as e:
                self.logger.error(f"Display Loop Error: {e}")
                time.sleep(0.1)

    def stop_detection(self):
        """
        Stops the detection pipeline and releases resources.
        """
        self.logger.info("Stopping detection pipeline...")
        try:
            self.running = False
            if hasattr(self, 'inference_thread'):
                self.inference_thread.join(timeout=1.0)
            
            self.camera.stop()
            self.inference.stop()
            cv2.destroyAllWindows()
            self.transport.send_status("inactive")
            self.logger.info("Detection pipeline Stopped.")
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")

    def _annotate_frame(self, frame, detections):
        """Draws bounding boxes and labels on the frame with optimization."""
        try:
            # We skip heavy JPEG encoding if not needed by the web dashboard,
            # or we rate-limit it.
            if not hasattr(self, '_last_encode_time'): self._last_encode_time = 0
            current_time = time.time()
            
            # Draw on a copy for the RPi screen
            annotated = frame.copy()
            
            for det in detections:
                bbox, label, conf = det.get("bbox"), det.get("class"), det.get("confidence")
                if bbox:
                    x1, y1, x2, y2 = bbox
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 1)
                    cv2.putText(annotated, f"{label} {conf:.2f}", (x1, y1 - 5), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
            
            cv2.putText(annotated, f"FPS: {self.fps:.2f}", (10, 20), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

            # Lazy JPEG encoding for web dashboard (~5 FPS enough for web)
            if current_time - self._last_encode_time >= 0.2:
                ret, jpeg = cv2.imencode('.jpg', annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
                if ret:
                    self.last_annotated_frame = jpeg.tobytes()
                    self._last_encode_time = current_time
            
            return annotated
        except Exception as e:
            self.logger.error(f"Failed to annotate frame: {e}")
            return frame
