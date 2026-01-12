import json
import datetime
from collections import defaultdict
from utils.logger import get_logger

class CountingAgent:
    def __init__(self, config_path="config/counting_config.json"):
        self.logger = get_logger(self.__class__.__name__)
        self.config = self._load_config(config_path)

    def _load_config(self, path):
        try:
            with open(path, 'r') as f:
                config = json.load(f)
                self.logger.info(f"Loaded counting config from {path}")
                return config
        except FileNotFoundError:
            self.logger.error(f"Config file not found: {path}")
            raise
        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON in config file: {path}")
            raise

    def count_objects(self, detections):
        """
        Dispatches to the appropriate counting method based on configuration.
        """
        method = self.config.get("method", "simple_count")
        
        if method == "simple_count":
            return self._simple_count(detections)
        else:
            self.logger.warning(f"Unknown counting method: {method}. Defaulting to simple_count.")
            return self._simple_count(detections)

    def _simple_count(self, detections):
        """
        Counts occurrences of each class in the detections list.
        Filters by 'classes_to_count' and 'min_confidence' if specified.
        """
        counts = defaultdict(int)
        # Note: In a real system, classes_to_count should be in config. 
        # For this implementation, we can support filtering if keys exist in config, 
        # otherwise count all provided detections.
        classes_to_count = self.config.get("classes_to_count", None) 
        min_conf = self.config.get("min_confidence", 0.0)

        for det in detections:
            class_name = det.get("class")
            confidence = det.get("confidence", 0.0)

            # Filter by confidence
            if confidence < min_conf:
                continue

            # Filter by class
            if classes_to_count and class_name not in classes_to_count:
                continue
            
            if class_name:
                counts[class_name] += 1

        # Format output
        result = dict(counts)
        result["total"] = sum(counts.values())
        result["timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"
        
        self.logger.debug(f"Count result: {result}")
        return result
