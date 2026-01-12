import time
import os
import psutil
import threading
from agents.orchestrator import Orchestrator

def monitor_system(duration_sec=300):
    print(f"\n--- Starting Stability Stress Test ({duration_sec}s) ---")
    orch = Orchestrator()
    
    # Start detection on its own thread to not block monitor
    print("Launching detection pipeline...")
    try:
        # We start it manually so we can monitor it in this script
        orch.camera.start()
        orch.inference.start()
        orch.running = True
        
        inf_thread = threading.Thread(target=orch._inference_loop, daemon=True)
        inf_thread.start()
        
        # Display logic needs main thread usually, but for test we run it headless
        # or just monitor the inference thread
        
        start_time = time.time()
        process = psutil.Process(os.getpid())
        
        print(f"{'Time':<10} | {'CPU %':<10} | {'RAM MB':<10} | {'Inf Thread':<12}")
        print("-" * 50)
        
        while time.time() - start_time < duration_sec:
            cpu = process.cpu_percent(interval=1.0)
            ram = process.memory_info().rss / (1024 * 1024)
            inf_alive = "ALIVE" if inf_thread.is_alive() else "DEAD!"
            
            elapsed = int(time.time() - start_time)
            print(f"{elapsed:>8}s | {cpu:>9.1f} | {ram:>9.1f} | {inf_alive:>12}")
            
            if not inf_thread.is_alive():
                print("\nCRITICAL: Inference thread died. Watchdog should trigger in real Orchestrator.")
                # Simulation: Watchdog would restart it.
            
            time.sleep(4)
            
    except KeyboardInterrupt:
        print("\nTest stopped by user.")
    finally:
        print("\nCleaning up test resources...")
        orch.stop_detection()
        print("Stability test completed.")

if __name__ == "__main__":
    monitor_system(300) # 5 minute test
