import cv2
import numpy as np
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config_loader import load_config
from utils.logger import setup_logger


class InferenceAgent:
    """Handles object detection inference using OpenCV DNN with YOLOv8 ONNX."""

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
        """Initialize inference agent with configuration.

        Args:
            config_path: Path to detection configuration JSON file
        """
        self.config = load_config(config_path)
        self.logger = setup_logger('InferenceAgent', '/home/digioptics_od/camera-system/logs/inference.log')
        self.net = None
        self.model_loaded = False

        # Extract config values with defaults
        self.model_path = self.config.get('model_path', '')
        self.confidence_threshold = self.config.get('confidence_threshold', 0.5)
        self.nms_threshold = self.config.get('nms_threshold', 0.45)
        self.classes_filter = self.config.get('classes', [])
        self.input_size = tuple(self.config.get('input_size', [640, 640]))

        self.logger.info(f"InferenceAgent initialized with model_path={self.model_path}, "
                        f"confidence={self.confidence_threshold}, nms={self.nms_threshold}, "
                        f"input_size={self.input_size}")
        if self.classes_filter:
            self.logger.info(f"Class filter enabled: {self.classes_filter}")

    def load_model(self):
        """Load ONNX model with OpenCV DNN backend.

        Returns:
            bool: True if model loaded successfully, False otherwise
        """
        try:
            # Check if model file exists
            if not os.path.exists(self.model_path):
                self.logger.error(f"Model file not found: {self.model_path}")
                self.logger.info("Attempting to download YOLOv8n ONNX model...")
                self._download_default_model()

            self.logger.info(f"Loading model from {self.model_path}")
            self.net = cv2.dnn.readNetFromONNX(self.model_path)

            # Set backend to CPU (for Raspberry Pi compatibility)
            self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

            self.model_loaded = True
            self.logger.info("Model loaded successfully (OpenCV DNN CPU backend)")
            return True

        except Exception as e:
            self.logger.error(f"Failed to load model: {e}")
            self.model_loaded = False
            return False

    def _download_default_model(self):
        """Download YOLOv8n ONNX model if not present.

        Raises:
            Exception: If download fails
        """
        import urllib.request

        model_url = "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.onnx"

        # Create directory if it doesn't exist
        model_dir = os.path.dirname(self.model_path)
        if model_dir:
            os.makedirs(model_dir, exist_ok=True)

        try:
            self.logger.info(f"Downloading model from {model_url}")
            urllib.request.urlretrieve(model_url, self.model_path)
            self.logger.info(f"Model downloaded successfully to {self.model_path}")
        except Exception as e:
            self.logger.error(f"Failed to download model: {e}")
            raise

    def preprocess(self, frame):
        """Preprocess frame for YOLOv8 inference.

        Args:
            frame: Input BGR image (numpy array)

        Returns:
            numpy.ndarray: Preprocessed blob ready for inference
        """
        # Create blob with normalization (0-255 -> 0-1), resize, and RGB conversion
        blob = cv2.dnn.blobFromImage(
            frame,
            scalefactor=1/255.0,
            size=self.input_size,
            swapRB=True,  # BGR to RGB
            crop=False
        )
        return blob

    def postprocess(self, outputs, frame_shape):
        """Post-process YOLOv8 outputs to extract detections.

        Args:
            outputs: Raw model outputs
            frame_shape: Original frame shape (height, width, channels)

        Returns:
            list: List of detection dictionaries with 'class', 'confidence', 'bbox'
        """
        detections = []

        # YOLOv8 output shape: (1, 84, 8400) where 84 = 4 bbox coords + 80 class scores
        output = outputs[0]

        # Transpose to (8400, 84) for easier processing
        output = output.transpose((0, 2, 1))[0]

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
        """Run full detection pipeline on a frame.

        Args:
            frame: Input BGR image (numpy array)

        Returns:
            list: List of detection dictionaries compatible with Firebase format
        """
        if not self.model_loaded or self.net is None:
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
            blob = self.preprocess(frame)

            # Run inference
            self.net.setInput(blob)
            outputs = self.net.forward()

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
        """Release model resources and free memory."""
        self.logger.info("Unloading model and releasing resources...")
        self.net = None
        self.model_loaded = False
        self.logger.info("Model unloaded successfully")

    def is_ready(self):
        """Check if model is loaded and ready for inference.

        Returns:
            bool: True if model is ready, False otherwise
        """
        return self.model_loaded and self.net is not None
