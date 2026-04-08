import time
import numpy as np
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.inference_agent_hailo import InferenceAgent

def benchmark():
    print("Starting Inference Benchmark...")
    try:
        agent = InferenceAgent()
        
        # Create dummy frame
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        
        # Benchmark loop
        num_frames = 100
        print(f"Running {num_frames} frames benchmark (stateful)...")
        
        agent.start()
        
        start_time = time.time()
        for i in range(num_frames):
            agent.run_inference(frame)
            if (i+1) % 10 == 0:
                print(f"Processed {i+1}/{num_frames} frames...")
        end_time = time.time()
        
        agent.stop()
        
        total_time = end_time - start_time
        fps = num_frames / total_time
        avg_latency = (total_time / num_frames) * 1000
        
        print("\n--- Benchmark Results ---")
        print(f"Total time: {total_time:.2f}s")
        print(f"Average throughput: {fps:.2f} FPS")
        print(f"Average latency: {avg_latency:.2f} ms")
        print("--------------------------")
        
    except Exception as e:
        print(f"Benchmark failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    benchmark()
