import sys
import os
import numpy as np
import logging

# Add project root to path so we can import agents
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.inference_agent_hailo import InferenceAgent
from utils.logger import get_logger

def verify_hailo():
    logger = get_logger("HailoVerifier")
    
    logger.info("Starting Hailo-8 Verification...")
    
    try:
        # 1. Initialize Inference Agent
        logger.info("Initializing Inference Agent (this loads the HEF model)...")
        agent = InferenceAgent()
        
        # 2. Create Dummy Frame (1080p black image)
        logger.info("Creating dummy frame (1920x1080)...")
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        
        # 3. Run Inference
        logger.info("Running inference on dummy frame...")
        detections = agent.run_inference(frame)
        
        # 4. Check Results
        logger.info(f"Inference completed. Detections: {detections}")
        logger.info("SUCCESS: Hailo-8 HAT+ appears to be functioning correctly for inference.")
        
    except ImportError as e:
        logger.error(f"FAILURE: Could not import required modules. Is 'hailo_platform' installed? Error: {e}")
    except FileNotFoundError as e:
        logger.error(f"FAILURE: Model file not found. Error: {e}")
    except RuntimeError as e:
        logger.error(f"FAILURE: Runtime error (possibly Hailo device issue). Error: {e}")
    except Exception as e:
        logger.error(f"FAILURE: Unexpected error: {e}")
        import traceback
        logger.debug(traceback.format_exc())

if __name__ == "__main__":
    verify_hailo()
