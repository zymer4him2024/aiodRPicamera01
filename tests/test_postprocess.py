import numpy as np
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.inference_agent_hailo import InferenceAgent

def test_postprocess_logic():
    print("Testing YOLOv8 Post-processing logic...")
    
    try:
        # Mocking initialization to avoid requiring the .hef file or SDK
        agent = InferenceAgent()
        
        # Create dummy Hailo NMS output: (1, 100, 6)
        # y1, x1, y2, x2, score, class_id
        mock_results = np.zeros((1, 100, 6), dtype=np.float32)
        
        # 1. Person: 0.9 confidence, (0.1, 0.1) to (0.5, 0.5)
        # Hailo format: y1, x1, y2, x2, score, class
        mock_results[0, 0] = [0.1, 0.1, 0.5, 0.5, 0.9, 0]
        
        # 2. Car: 0.85 confidence, (0.2, 0.2) to (0.6, 0.6)
        mock_results[0, 1] = [0.2, 0.2, 0.6, 0.6, 0.85, 2]
        
        # 3. Motorcycle: 0.4 confidence (below threshold in config=0.5)
        mock_results[0, 2] = [0.1, 0.1, 0.3, 0.3, 0.4, 3]
        
        # 4. Unknown class: class 10
        mock_results[0, 3] = [0.5, 0.5, 0.8, 0.8, 0.95, 10]
        
        original_dims = (1920, 1080)
        input_dims = (640, 640)
        
        # Wrap in dict as InferVStreams.infer() would
        raw_detections = {"output_vstream": mock_results}
        
        detections = agent._postprocess(raw_detections, original_dims, input_dims)
        
        print(f"Detections found: {len(detections)}")
        for d in detections:
            print(f" - {d['class']}: {d['confidence']:.2f} @ {d['bbox']}")

        # Validation
        # Expected:
        # 1. Person (score 0.9) -> bbox [x1*1920, y1*1080, x2*1920, y2*1080] = [192, 108, 960, 540]
        # 2. Car (score 0.85) -> bbox [x1*1920, y1*1080, x2*1920, y2*1080] = [384, 216, 1152, 648]
        
        if len(detections) != 2:
            print(f"FAILURE: Expected 2 detections, got {len(detections)}")
            return False
            
        if detections[0]['class'] != 'person' or detections[1]['class'] != 'car':
             print(f"FAILURE: Classes mismatch. Got {detections[0]['class']} and {detections[1]['class']}")
             return False
             
        print("SUCCESS: Post-processing logic verified.")
        return True

    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if test_postprocess_logic():
        sys.exit(0)
    else:
        sys.exit(1)
