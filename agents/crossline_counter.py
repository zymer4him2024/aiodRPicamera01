"""
Crossline Counter Agent
Tracks objects crossing a user-defined line for directional counting.
"""

import time
from google.cloud import firestore
from utils.logger import get_logger


class CrosslineCounter:
    def __init__(self, binding_manager):
        self.logger = get_logger(self.__class__.__name__)
        self.binding = binding_manager
        self.db = firestore.Client()
        
        # Crossline configuration
        self.crossline = None
        self.last_crossline_check = 0
        self.crossline_check_interval = 10  # Check for updates every 10 seconds
        
        # Object tracking
        self.tracked_objects = {}  # {object_id: [prev_centroid, curr_centroid]}
        self.crossline_count = 0
        
        # Load initial crossline
        self._load_crossline()
        
    def _load_crossline(self):
        """Load crossline configuration from Firestore"""
        try:
            camera_ref = self.db.collection('cameras').where('camera_id', '==', self.binding.camera_id).limit(1).stream()
            for doc in camera_ref:
                data = doc.data()
                if 'crossline' in data and data['crossline']:
                    self.crossline = data['crossline']
                    p1 = self.crossline['point1']
                    p2 = self.crossline['point2']
                    self.logger.info(f"Loaded crossline: ({p1['x']},{p1['y']}) to ({p2['x']},{p2['y']})")
                else:
                    self.logger.info("No crossline configured for this camera")
                return
        except Exception as e:
            self.logger.error(f"Failed to load crossline: {e}")
    
    def _check_for_crossline_updates(self):
        """Periodically check if crossline has been updated"""
        now = time.time()
        if now - self.last_crossline_check > self.crossline_check_interval:
            self._load_crossline()
            self.last_crossline_check = now
    
    def _line_intersection(self, p1, p2, p3, p4):
        """
        Check if line segment p1-p2 intersects with line segment p3-p4.
        Uses parametric line equation and cross product method.
        
        Args:
            p1, p2: First line segment endpoints (dict with 'x', 'y')
            p3, p4: Second line segment endpoints (dict with 'x', 'y')
            
        Returns:
            bool: True if lines intersect, False otherwise
        """
        def ccw(A, B, C):
            """Check if three points are in counter-clockwise order"""
            return (C['y'] - A['y']) * (B['x'] - A['x']) > (B['y'] - A['y']) * (C['x'] - A['x'])
        
        # Two segments intersect if endpoints are on opposite sides of each other
        return (ccw(p1, p3, p4) != ccw(p2, p3, p4) and 
                ccw(p1, p2, p3) != ccw(p1, p2, p4))
    
    def _get_direction(self, prev_point, curr_point, line_p1, line_p2):
        """
        Determine which direction object crossed the line.
        Uses cross product to detect positive (left-to-right/top-to-bottom) crossing.
        
        Returns:
            int: 1 for positive direction, -1 for negative, 0 for no crossing
        """
        # Calculate cross products to see which side of line each point is on
        def cross_product(p1, p2, point):
            return ((p2['x'] - p1['x']) * (point['y'] - p1['y']) - 
                    (p2['y'] - p1['y']) * (point['x'] - p1['x']))
        
        prev_side = cross_product(line_p1, line_p2, prev_point)
        curr_side = cross_product(line_p1, line_p2, curr_point)
        
        # Crossing detected if signs differ
        if prev_side * curr_side < 0:
            # Positive direction: prev was negative side, curr is positive side
            if prev_side < 0 and curr_side > 0:
                return 1
            else:
                return -1
        return 0
    
    def process(self, detections, frame_width, frame_height):
        """
        Process detections and count crossline crossings.
        
        Args:
            detections: List of detection dicts with 'object_id', 'bbox', 'class_name'
            frame_width: Width of the frame (for normalizing coordinates)
            frame_height: Height of the frame (for normalizing coordinates)
            
        Returns:
            int: Current crossline count
        """
        # Check for crossline updates periodically
        self._check_for_crossline_updates()
        
        # Skip if no crossline configured
        if not self.crossline:
            return 0
        
        # Process each detected object
        current_frame_ids = set()
        
        for detection in detections:
            obj_id = detection.get('object_id')
            bbox = detection.get('bbox')
            
            if not obj_id or not bbox:
                continue
            
            current_frame_ids.add(obj_id)
            
            # Calculate centroid (normalized 0-1)
            x1, y1, x2, y2 = bbox
            centroid = {
                'x': ((x1 + x2) / 2) / frame_width,
                'y': ((y1 + y2) / 2) / frame_height
            }
            
            # Check if we have previous position for this object
            if obj_id in self.tracked_objects:
                prev_centroid = self.tracked_objects[obj_id]['curr']
                
                # Check for line crossing
                if self._line_intersection(
                    prev_centroid, 
                    centroid, 
                    self.crossline['point1'], 
                    self.crossline['point2']
                ):
                    # Determine direction
                    direction = self._get_direction(
                        prev_centroid,
                        centroid,
                        self.crossline['point1'],
                        self.crossline['point2']
                    )
                    
                    # Only count positive direction (as per requirements)
                    if direction == 1:
                        self.crossline_count += 1
                        self.logger.info(f"Object {obj_id} crossed line! Total count: {self.crossline_count}")
            
            # Update tracked position
            self.tracked_objects[obj_id] = {
                'prev': self.tracked_objects.get(obj_id, {}).get('curr', centroid),
                'curr': centroid
            }
        
        # Remove objects that are no longer detected
        disappeared_ids = set(self.tracked_objects.keys()) - current_frame_ids
        for obj_id in disappeared_ids:
            del self.tracked_objects[obj_id]
        
        return self.crossline_count
    
    def reset_count(self):
        """Reset the crossline count to zero"""
        self.crossline_count = 0
        self.logger.info("Crossline count reset")
