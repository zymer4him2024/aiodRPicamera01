import json
import os
import time
import numpy as np
import cv2
import traceback
from utils.logger import get_logger

# Import Hailo Platform API
try:
    from hailo_platform import (
        HEF,
        VDevice,
        HailoStreamInterface,
        InferVStreams,
        ConfigureParams,
        InputVStreamParams,
        OutputVStreamParams,
        FormatType
    )
except ImportError:
    # This allows the code to be syntax-checked in environments without the SDK
    HEF = None
    VDevice = None

class InferenceAgent:
    def __init__(self, config_path="config/detection_config.json"):
        self.logger = get_logger(self.__class__.__name__)
        self.config = self._load_config(config_path)
        self.target = None
        self.network_group = None
        self.network_group_params = None
        self.input_vstreams_params = None
        self.output_vstreams_params = None
        self.hef = None
        self.input_vstream_info = None
        self.output_vstream_info = None
        
        # Runtime state
        self.is_running = False
        self.infer_pipeline = None
        self.activation_context = None
        
        # Check for Hailo SDK availability
        if HEF is None:
            self.logger.error("Hailo SDK not installed or 'hailo_platform' not found.")
            # We don't raise immediately to allow purely structural tests, 
            # but in production this should fail.
        
        self._initialize_model()

    def _load_config(self, path):
        try:
            with open(path, 'r') as f:
                config = json.load(f)
                self.logger.info(f"Loaded detection config from {path}")
                return config
        except FileNotFoundError:
            self.logger.error(f"Config file not found: {path}")
            raise
        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON in config file: {path}")
            raise

    def _initialize_model(self):
        if HEF is None:
            return

        model_path = self.config.get("model_path")
        if not model_path or not os.path.exists(model_path):
            self.logger.error(f"Model file not found: {model_path}")
            raise FileNotFoundError(f"Model file not found: {model_path}")

        try:
            self.logger.info(f"Loading HEF model: {model_path}")
            self.hef = HEF(model_path)
            
            # Configure Params
            self.configure_params = ConfigureParams.create_from_hef(
                self.hef, interface=HailoStreamInterface.PCIe)
            
            self.target = VDevice()
            self.network_groups = self.target.configure(self.hef, self.configure_params)
            self.network_group = self.network_groups[0]
            self.network_group_params = self.network_group.create_params()

            self.input_vstreams_params = InputVStreamParams.make_from_network_group(
                self.network_group, quantized=True, format_type=FormatType.UINT8
            )
            self.output_vstreams_params = OutputVStreamParams.make_from_network_group(
                self.network_group, format_type=FormatType.FLOAT32
            )
            
            # Extract names for mapping data
            self.input_vstream_info = self.hef.get_input_vstream_infos()
            self.output_vstream_info = self.hef.get_output_vstream_infos()
            
            for info in self.input_vstream_info:
                self.logger.info(f"Input vstream: {info.name}, Shape: {info.shape}")
            for info in self.output_vstream_info:
                self.logger.info(f"Output vstream: {info.name}, Shape: {info.shape}")
            
            self.logger.info("Hailo-8 accelerator initialized successfully.")

        except Exception as e:
            self.logger.error(f"Failed to initialize Hailo-8 device: {e}")
            raise RuntimeError(f"Hailo device initialization failed: {e}")

    def _preprocess(self, frame, input_shape):
        """
        Resizes and normalizes the frame for the model.
        input_shape: (width, height)
        """
        h, w, _ = frame.shape
        input_w, input_h = input_shape
        
        resized_frame = cv2.resize(frame, (input_w, input_h))
        
        # UINT8 input - no normalization needed
        processed_frame = resized_frame.astype(np.uint8)
        
        # Add batch dimension - Required by HailoRT InferVStreams.infer()
        processed_frame = np.expand_dims(processed_frame, axis=0)
        
        return processed_frame.astype(np.uint8), w, h

    def _postprocess(self, raw_detections, original_dims, input_dims):
        """
        Parses raw output, applies NMS, and filters by class.
        This is a simplified placeholders as raw_detections structure depends heavily 
        on the specific model architecture (e.g., YOLO output layer).
        
        Assuming raw_detections is a dictionary {output_name: data}.
        """
        # Placeholder for complex YOLOv8 post-processing logic
        # In a real scenario, we'd need to interpret the output tensors (boxes, scores, classes)
        # For this agent, we will simulate the return format based on requirements.
        
        detections = []
        
        # Real post-processing implementation would go here:
        # 1. Extract boxes, objectness, class_probs
        # 2. Filter by confidence_threshold
        # 3. Apply NMS
        # 4. Scale boxes back to original_dims
        
        # Since we don't have the specific output tensor layout of the compiled HEF,
        # we return an empty list or specific format as required.
        
        detections = []
        conf_thresh = self.config.get("confidence_threshold", 0.5)
        orig_w, orig_h = original_dims
        
        # COCO class mapping for the requested objects
        # 0: person, 2: car, 3: motorcycle, 5: bus, 7: truck
        class_map = {
            0: "Pedestrians",
            2: "Cars",
            3: "Motorcycles",
            5: "Buses",
            7: "Trucks"
        }

        try:
            self.logger.info(f"V11_NUCLEAR_PARSER: Input type {type(raw_detections)}")
            
            # 1. Handle Dict wrapper
            if isinstance(raw_detections, dict):
                if not raw_detections: return []
                results = list(raw_detections.values())[0]
            else:
                results = raw_detections

            # 2. Defensively find the detection data
            # We avoid any high-level numpy operations that trigger "inhomogeneous shape" errors.
            
            # Helper to find if a variable is "class-separated" (length 80)
            def is_coco_separated(data):
                try:
                    return len(data) == 80 and not isinstance(data[0], (int, float))
                except:
                    return False

            # Helper to safely iterate anything
            def safe_get_detections(data_node, depth=0):
                if depth > 3: return # Safety limit
                
                # If it's a batch wrapper [Results]
                if isinstance(data_node, (list, tuple, np.ndarray)) and len(data_node) == 1:
                    safe_get_detections(data_node[0], depth + 1)
                    return

                # If it's class-separated (80 lists)
                if is_coco_separated(data_node):
                    for c_id, category_results in enumerate(data_node):
                        if c_id in class_map:
                            label = class_map[c_id]
                            for det in category_results:
                                if len(det) >= 5:
                                    score = float(det[4])
                                    if score >= conf_thresh:
                                        y1, x1, y2, x2 = float(det[0]), float(det[1]), float(det[2]), float(det[3])
                                        detections.append({
                                            "class": label, "confidence": score,
                                            "bbox": [int(x1 * orig_w), int(y1 * orig_h), int(x2 * orig_w), int(y2 * orig_h)]
                                        })
                    return

                # If it's a flat list of detections
                if isinstance(data_node, (list, tuple, np.ndarray)):
                    for det in data_node:
                        if len(det) >= 6:
                            score = float(det[4])
                            c_id = int(det[5])
                            if score >= conf_thresh and c_id in class_map:
                                label = class_map[c_id]
                                y1, x1, y2, x2 = float(det[0]), float(det[1]), float(det[2]), float(det[3])
                                detections.append({
                                    "class": label, "confidence": score,
                                    "bbox": [int(x1 * orig_w), int(y1 * orig_h), int(x2 * orig_w), int(y2 * orig_h)]
                                })

            safe_get_detections(results)

        except Exception as e:
            self.logger.error(f"V11_CRITICAL_FAIL: {e}")
            self.logger.debug(traceback.format_exc())
            
        return detections

    def start(self):
        """
        Activates the Hailo network and initializes the inference pipeline.
        Must be called before run_inference.
        """
        if self.network_group is None or HEF is None:
            self.logger.error("Cannot start: Hailo device not initialized.")
            return

        if self.is_running:
            self.logger.warning("InferenceAgent is already running.")
            return

        try:
            self.logger.info("Activating Hailo network group...")
            self.activation_context = self.network_group.activate(self.network_group_params)
            self.activation_context.__enter__()
            
            self.logger.info("Initializing InferVStreams pipeline...")
            self.infer_pipeline = InferVStreams(
                self.network_group, 
                self.input_vstreams_params, 
                self.output_vstreams_params
            )
            self.infer_pipeline.__enter__()
            
            self.is_running = True
            self.logger.info("InferenceAgent started and ready.")
        except Exception as e:
            self.logger.error(f"Failed to start InferenceAgent: {e}")
            self.stop()
            raise

    def stop(self):
        """
        Deactivates the Hailo network and releases pipeline resources.
        """
        self.logger.info("Stopping InferenceAgent...")
        self.is_running = False
        
        if self.infer_pipeline:
            try:
                self.infer_pipeline.__exit__(None, None, None)
            except Exception as e:
                self.logger.error(f"Error exiting infer pipeline: {e}")
            self.infer_pipeline = None

        if self.activation_context:
            try:
                self.activation_context.__exit__(None, None, None)
            except Exception as e:
                self.logger.error(f"Error exiting activation context: {e}")
            self.activation_context = None
        
        self.logger.info("InferenceAgent stopped.")

    def run_inference(self, frame):
        """
        Runs inference on a single frame.
        """
        if not self.is_running or self.infer_pipeline is None:
             self.logger.error("Inference attempted but agent is not started.")
             return []

        try:
            input_shape = self.config.get("input_size", [640, 640])
            processed_input, orig_w, orig_h = self._preprocess(frame, tuple(input_shape))
            
            # Use the pre-activated pipeline for inference
            infer_results = self.infer_pipeline.infer(processed_input)
            
            detections = self._postprocess(infer_results, (orig_w, orig_h), input_shape)
            self.logger.debug(f"Inference complete: {len(detections)} objects found")
            return detections

        except Exception as e:
            self.logger.error(f"Inference CRITICAL error: {e}")
            return []
