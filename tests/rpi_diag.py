import cv2
import time
import numpy as np
import os
import json

def test_camera():
    print("\n--- Testing Camera ---")
    try:
        with open("config/camera_config.json", "r") as f:
            config = json.load(f)
        device_id = config.get("device_id", 0)
        print(f"Opening camera {device_id}...")
        cap = cv2.VideoCapture(device_id)
        if not cap.isOpened():
            print("ERROR: Camera could not be opened.")
            return False
        
        print("Reading 5 frames...")
        for i in range(5):
            ret, frame = cap.read()
            if not ret:
                print(f"ERROR: Failed to read frame {i}")
                cap.release()
                return False
            print(f"Captured frame {i} - Shape: {frame.shape}")
        
        cap.release()
        print("Camera test PASSED.")
        return True
    except Exception as e:
        print(f"Camera test failed with error: {e}")
        return False

def test_hailo():
    print("\n--- Testing Hailo ---")
    try:
        from hailo_platform import HEF, VDevice, InferVStreams, ConfigureParams, HailoStreamInterface, InputVStreamParams, OutputVStreamParams, FormatType
    except ImportError:
        print("ERROR: hailo_platform SDK not found.")
        return False

    try:
        with open("config/detection_config.json", "r") as f:
            config = json.load(f)
        model_path = config.get("model_path")
        if not os.path.exists(model_path):
            print(f"ERROR: Model file not found at {model_path}")
            return False
        
        print(f"Loading HEF: {model_path}")
        hef = HEF(model_path)
        print("Initializing VDevice...")
        target = VDevice()
        print("Configuring network group...")
        configure_params = ConfigureParams.create_from_hef(hef, interface=HailoStreamInterface.PCIe)
        network_groups = target.configure(hef, configure_params)
        network_group = network_groups[0]
        network_group_params = network_group.create_params()
        
        input_vstreams_params = InputVStreamParams.make_from_network_group(network_group, quantized=True, format_type=FormatType.UINT8)
        output_vstreams_params = OutputVStreamParams.make_from_network_group(network_group, format_type=FormatType.FLOAT32)
        
        print("Activating network and running dummy inference...")
        with network_group.activate(network_group_params):
            with InferVStreams(network_group, input_vstreams_params, output_vstreams_params) as infer_pipeline:
                input_data = np.random.randint(0, 255, (1, 640, 640, 3), dtype=np.uint8)
                print("Starting infer call...")
                res = infer_pipeline.infer(input_data)
                print("Infer call returned.")
                if res:
                    print(f"Inference SUCCESS. Outputs: {list(res.keys())}")
                else:
                    print("Inference returned empty.")
        
        print("Hailo test PASSED.")
        return True
    except Exception as e:
        print(f"Hailo test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    cam_ok = test_camera()
    hailo_ok = test_hailo()
    
    if cam_ok and hailo_ok:
        print("\nSUMMARY: Both Camera and Hailo are working correctly.")
        print("The issue is likely in the agent state management or service configuration.")
    else:
        print("\nSUMMARY: Errors found. See logs above.")
