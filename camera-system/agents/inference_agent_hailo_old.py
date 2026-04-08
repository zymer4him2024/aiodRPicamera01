import numpy as np
import sys
import os
from hailo_platform import (
    VDevice,
    HailoStreamInterface,
    InferVStreams,
    ConfigureParams,
    InputVStreamParams,
    OutputVStreamParams,
    FormatType
)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config_loader import load_config
from utils.logger import setup_logger


class InferenceAgentHailo:
    """Handles object detection inference using Hailo-8 accelerator with YOLOv8 HEF."""

    # COCO class names (YOLOv8 default - 80 classes)
    COCO_CLASSES = [
        'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck',
        'boat', 'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench',
        'bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra',
        'giraffe', 'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee',
        'skis', 'snowboard', 'sports ball', 'kite', 'baseball bat', 'baseball glove',
        'skateboard', 'surfboard', 'tennis racket', 'bottle', 'wine glass', 'cup',
        'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple', 'sandwich', 'orange',
        'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch',
        'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse',
        'remote', 'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink',
        'refrigerator', 'book', 'clock', 'vase', 'scissors', 'teddy bear', 'hair drier',
        'toothbrush'
    ]

    def __init__(self, config_path):
        """Initialize Hailo inference agent with configuration.

        Args:
            config_path: Path to detection configuration JSON file
        """
        self.config = load_config(config_path)
        self.logger = setup_logger('InferenceAgentHailo', '/home/digioptics_od/camera-system/logs/inference.log')

        self.vdevice = None
        self.hef = None
        self.network_group = None
        self.network_group_params = None
        self.input_vstreams_params = None
        self.output_vstreams_params = None
        self.model_loaded = False

        # Extract config values with defaults
        self.model_path = self.config.get('model_path', '')
        self.confidence_threshold = self.config.get('confidence_threshold', 0.5)
        self.nms_threshold = self.config.get('nms_threshold', 0.45)
        self.classes_filter = self.config.get('classes', [])
        self.input_size = tuple(self.config.get('input_size', [640, 640]))

        self.logger.info(f"InferenceAgentHailo initialized with model_path={self.model_path}, "
                        f"confidence={self.confidence_threshold}, nms={self.nms_threshold}, "
                        f"input_size={self.input_size}")
        if self.classes_filter:
            self.logger.info(f"Class filter enabled: {self.classes_filter}")

    def load_model(self):
        """Load HEF model with Hailo-8 accelerator.

        Returns:
            bool: True if model loaded successfully, False otherwise
        """
        try:
            # Check if model file exists
            if not os.path.exists(self.model_path):
                self.logger.error(f"HEF model file not found: {self.model_path}")
                self.logger.error("Please ensure YOLOv8 model is compiled to HEF format")
                return False

            self.logger.info(f"Loading HEF model from {self.model_path}")

            # Create VDevice (represents Hailo device)
            params = VDevice.create_params()
            params.device_count = 1
            self.vdevice = VDevice(params)

            # Load HEF file
            self.hef = self.vdevice.create_hef_file(self.model_path)

            # Configure network group
            configure_params = ConfigureParams.create_from_hef(self.hef, interface=HailoStreamInterface.PCIe)
            self.network_group = self.vdevice.configure(self.hef, configure_params)[0]

            # Get network group parameters
            self.network_group_params = self.network_group.create_params()

            # Get input/output stream parameters
            self.input_vstreams_params = InputVStreamParams.make_from_network_group(
                self.network_group,
                quantized=False,
                format_type=FormatType.FLOAT32
            )

            self.output_vstreams_params = OutputVStreamParams.make_from_network_group(
                self.network_group,
                quantized=False,
                format_type=FormatType.FLOAT32
            )

            self.model_loaded = True
            self.logger.info("HEF model loaded successfully on Hailo-8")
            return True

        except Exception as e:
            self.logger.error(f"Failed to load HEF model: {e}")
            self.model_loaded = False
            return False

    def preprocess(self, frame):
        """Preprocess frame for YOLOv8 inference on Hailo.

        Args:
            frame: Input BGR image (numpy array)

        Returns:
            numpy.ndarray: Preprocessed frame ready for Hailo inference
        """
        import cv2

        # Resize to model input size
        resized = cv2.resize(frame, self.input_size)

        # Convert BGR to RGB
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

        # Normalize to 0-1 range and convert to float32
        normalized = rgb.astype(np.float32) / 255.0

        # Add batch dimension: (H, W, C) -> (1, H, W, C)
        batched = np.expand_dims(normalized, axis=0)

        return batched

    def postprocess(self, outputs, frame_shape):
        """Post-process YOLOv8 outputs from Hailo to extract detections.

        Args:
            outputs: Raw model outputs from Hailo
            frame_shape: Original frame shape (height, width, channels)

        Returns:
            list: List of detection dictionaries with 'class', 'confidence', 'bbox'
        """
        import cv2

        detections = []

        # Get the first output (YOLOv8 typically has one main output)
        # Expected shape: (1, 84, 8400) where 84 = 4 bbox coords + 80 class scores
        output = outputs[0]

        # Remove batch dimension and transpose to (8400, 84)
        if len(output.shape) == 3:
            output = output[0].transpose()

        rows = output.shape[0]

        boxes = []
        scores = []
        class_ids = []

        # Original frame dimensions
        img_height, img_width = frame_shape[:2]

        # Calculate scale factors for bbox coordinate conversion
        x_factor = img_width / self.input_size[0]
        y_factor = img_height / self.input_size[1]

        # Process each detection
        for i in range(rows):
            # Extract class scores (columns 4 onwards)
            classes_scores = output[i][4:]
            max_score = np.amax(classes_scores)

            # Apply confidence threshold
            if max_score >= self.confidence_threshold:
                class_id = np.argmax(classes_scores)
                class_name = self.COCO_CLASSES[class_id] if class_id < len(self.COCO_CLASSES) else f"class_{class_id}"

                # Filter by configured classes (if specified)
                if self.classes_filter and class_name not in self.classes_filter:
                    continue

                # Extract bbox coordinates (cx, cy, w, h format in YOLOv8)
                cx, cy, w, h = output[i][0:4]

                # Scale to original image dimensions
                cx *= x_factor
                cy *= y_factor
                w *= x_factor
                h *= y_factor

                # Convert center format to corner format (x1, y1, width, height) for NMS
                x1 = int(cx - w / 2)
                y1 = int(cy - h / 2)
                width = int(w)
                height = int(h)

                boxes.append([x1, y1, width, height])
                scores.append(float(max_score))
                class_ids.append((class_id, class_name))

        # Apply Non-Maximum Suppression to remove duplicate detections
        if len(boxes) > 0:
            indices = cv2.dnn.NMSBoxes(boxes, scores, self.confidence_threshold, self.nms_threshold)

            if len(indices) > 0:
                for i in indices.flatten():
                    box = boxes[i]
                    x1 = box[0]
                    y1 = box[1]
                    x2 = x1 + box[2]
                    y2 = y1 + box[3]

                    # Ensure bbox is within frame boundaries
                    x1 = max(0, min(x1, img_width - 1))
                    y1 = max(0, min(y1, img_height - 1))
                    x2 = max(0, min(x2, img_width - 1))
                    y2 = max(0, min(y2, img_height - 1))

                    detections.append({
                        'class': class_ids[i][1],
                        'confidence': scores[i],
                        'bbox': [x1, y1, x2, y2]  # [x1, y1, x2, y2] format
                    })

        return detections

    def detect(self, frame):
        """Run full detection pipeline on a frame using Hailo-8.

        Args:
            frame: Input BGR image (numpy array)

        Returns:
            list: List of detection dictionaries compatible with Firebase format
        """
        if not self.model_loaded or self.network_group is None:
            self.logger.warning("Model not loaded, cannot perform detection")
            return []

        if frame is None:
            self.logger.warning("Invalid frame provided (None)")
            return []

        if len(frame.shape) != 3:
            self.logger.error(f"Invalid frame shape: {frame.shape}, expected 3D array")
            return []

        try:
            # Preprocess frame
            input_data = self.preprocess(frame)

            # Run inference using Hailo
            with InferVStreams(self.network_group, self.input_vstreams_params, self.output_vstreams_params) as infer_pipeline:
                # Create input dictionary (key = layer name, value = data)
                input_dict = {list(infer_pipeline.input_vstreams.keys())[0]: input_data}

                # Run inference
                output_dict = infer_pipeline.infer(input_dict)

                # Extract outputs as list
                outputs = list(output_dict.values())

            # Post-process outputs
            detections = self.postprocess(outputs, frame.shape)

            if detections:
                self.logger.debug(f"Detected {len(detections)} objects")
            else:
                self.logger.debug("No objects detected")

            return detections

        except Exception as e:
            self.logger.error(f"Detection error: {e}")
            return []

    def unload_model(self):
        """Release Hailo resources and free memory."""
        self.logger.info("Unloading Hailo model and releasing resources...")

        try:
            if self.network_group is not None:
                self.network_group = None

            if self.hef is not None:
                self.hef = None

            if self.vdevice is not None:
                self.vdevice = None

            self.model_loaded = False
            self.logger.info("Hailo model unloaded successfully")

        except Exception as e:
            self.logger.error(f"Error during model unload: {e}")

    def is_ready(self):
        """Check if Hailo model is loaded and ready for inference.

        Returns:
            bool: True if model is ready, False otherwise
        """
        return self.model_loaded and self.network_group is not None
