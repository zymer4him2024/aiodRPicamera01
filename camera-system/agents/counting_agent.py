import sys
import os
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config_loader import load_config
from utils.logger import setup_logger


class CountingAgent:
    """Handles object counting logic with configurable filtering and methods."""

    def __init__(self, config_path):
        """Initialize counting agent with configuration.

        Args:
            config_path: Path to counting configuration JSON file
        """
        self.config = load_config(config_path)
        self.logger = setup_logger('CountingAgent', '/home/digioptics_od/camera-system/logs/counting.log')

        # Extract config values with defaults
        self.method = self.config.get('method', 'simple_count')
        self.classes_to_count = self.config.get('classes_to_count', [])
        self.min_confidence = self.config.get('min_confidence', 0.6)

        self.logger.info(f"CountingAgent initialized with method={self.method}, "
                        f"min_confidence={self.min_confidence}")
        if self.classes_to_count:
            self.logger.info(f"Counting classes: {self.classes_to_count}")
        else:
            self.logger.info("Counting all detected classes")

    def count(self, detections):
        """Count objects from detections with filtering.

        Args:
            detections: List of detection dictionaries
                Format: [
                    {'class': 'person', 'confidence': 0.95, 'bbox': [x1, y1, x2, y2]},
                    {'class': 'car', 'confidence': 0.87, 'bbox': [...]}
                ]

        Returns:
            dict: Counts dictionary in Firebase ingestCounts format
                Format: {
                    'person': 2,
                    'car': 1,
                    'timestamp': '2025-01-09T18:30:00Z',
                    'total': 3
                }
        """
        if not detections:
            self.logger.debug("No detections to count")
            return self._empty_counts()

        # Filter detections by class and confidence
        filtered = []
        for det in detections:
            try:
                class_name = det.get('class', '')
                confidence = det.get('confidence', 0.0)

                # Validate detection has required fields
                if not class_name:
                    self.logger.warning("Detection missing 'class' field, skipping")
                    continue

                # Filter by class list (if configured)
                if self.classes_to_count and class_name not in self.classes_to_count:
                    self.logger.debug(f"Skipping class '{class_name}' (not in classes_to_count)")
                    continue

                # Filter by minimum confidence threshold
                if confidence < self.min_confidence:
                    self.logger.debug(f"Skipping {class_name} with confidence {confidence:.2f} "
                                    f"(below threshold {self.min_confidence})")
                    continue

                filtered.append(det)

            except Exception as e:
                self.logger.warning(f"Invalid detection format, skipping: {e}")
                continue

        # Count objects by class using selected method
        if self.method == 'simple_count':
            counts = self._simple_count(filtered)
        else:
            self.logger.warning(f"Unknown counting method '{self.method}', using simple_count")
            counts = self._simple_count(filtered)

        # Calculate total count
        total = sum(v for k, v in counts.items() if k not in ['timestamp', 'total'])

        # Add metadata
        counts['timestamp'] = datetime.utcnow().isoformat() + 'Z'
        counts['total'] = total

        if total > 0:
            self.logger.info(f"Counted {total} objects: {counts}")
        else:
            self.logger.debug("No objects met counting criteria")

        return counts

    def _simple_count(self, detections):
        """Simple counting method - count each detection once.

        Args:
            detections: List of filtered detection dictionaries

        Returns:
            dict: Class counts dictionary
        """
        counts = {}

        for det in detections:
            class_name = det['class']
            counts[class_name] = counts.get(class_name, 0) + 1

        return counts

    def _empty_counts(self):
        """Return empty counts structure with zero counts for configured classes.

        Returns:
            dict: Empty counts dictionary with timestamp and total
        """
        counts = {}

        # Initialize configured classes to 0
        if self.classes_to_count:
            for class_name in self.classes_to_count:
                counts[class_name] = 0

        # Add metadata
        counts['timestamp'] = datetime.utcnow().isoformat() + 'Z'
        counts['total'] = 0

        return counts

    def get_config(self):
        """Get current counting configuration.

        Returns:
            dict: Current configuration settings
        """
        return {
            'method': self.method,
            'classes_to_count': self.classes_to_count,
            'min_confidence': self.min_confidence
        }

    def update_min_confidence(self, new_threshold):
        """Update minimum confidence threshold dynamically.

        Args:
            new_threshold: New confidence threshold (0.0 to 1.0)

        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            if not 0.0 <= new_threshold <= 1.0:
                self.logger.error(f"Invalid confidence threshold: {new_threshold} (must be 0.0-1.0)")
                return False

            old_threshold = self.min_confidence
            self.min_confidence = new_threshold
            self.logger.info(f"Updated min_confidence: {old_threshold} -> {new_threshold}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to update min_confidence: {e}")
            return False
