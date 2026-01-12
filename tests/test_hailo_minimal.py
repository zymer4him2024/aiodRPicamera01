import numpy as np
from hailo_platform import (HEF, VDevice, HailoStreamInterface, InferVStreams, ConfigureParams,
    InputVStreamParams, OutputVStreamParams, FormatType)

def test_minimal():
    hef_path = "models/yolov8n.hef"
    hef = HEF(hef_path)
    
    with VDevice() as target:
        configure_params = ConfigureParams.create_from_hef(hef, interface=HailoStreamInterface.PCIe)
        network_group = target.configure(hef, configure_params)[0]
        network_group_params = network_group.create_params()
        
        input_vstreams_params = InputVStreamParams.make(network_group, format_type=FormatType.UINT8)
        output_vstreams_params = OutputVStreamParams.make(network_group, format_type=FormatType.FLOAT32)
        
        input_vstream_info = hef.get_input_vstream_infos()
        input_name = input_vstream_info[0].name
        print(f"Input name: {input_name}")
        print(f"Input shape: {input_vstream_info[0].shape}")
        
        # Create dummy data (1, 640, 640, 3) UINT8
        data = np.zeros((1, 640, 640, 3), dtype=np.uint8)
        
        with network_group.activate(network_group_params):
            with InferVStreams(network_group, input_vstreams_params, output_vstreams_params) as infer_pipeline:
                print("Running inference...")
                # Try direct array first
                try:
                    results = infer_pipeline.infer(data)
                    print("Inference success with direct array!")
                except Exception as e:
                    print(f"Direct array failed: {e}")
                    # Try dictionary next
                    try:
                        results = infer_pipeline.infer({input_name: data})
                        print("Inference success with dictionary!")
                    except Exception as e:
                        print(f"Dictionary failed: {e}")
                        
if __name__ == "__main__":
    test_minimal()
