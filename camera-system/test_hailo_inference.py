#!/usr/bin/env python3
"""
Test script for Hailo-8 inference functionality.
Tests Hailo SDK, model loading, and inference performance.
"""

import sys
import os
import cv2
import time
import numpy as np

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.inference_agent_hailo import InferenceAgentHailo
from utils.logger import setup_logger


def test_hailo_sdk():
    """Test Hailo SDK installation and device detection."""
    print("\n" + "="*60)
    print("TEST 1: Hailo SDK and Device Detection")
    print("="*60)

    try:
        from hailo_platform import VDevice

        # Create VDevice to detect Hailo hardware
        params = VDevice.create_params()
        params.device_count = 1

        print("Attempting to create VDevice...")
        vdevice = VDevice(params)

        print("✅ Hailo SDK installed correctly")
        print("✅ Hailo device detected")

        # Try to get device info (API varies by version)
        try:
            if hasattr(vdevice, 'get_physical_devices_infos'):
                device_info = vdevice.get_physical_devices_infos()[0]
                print(f"   Device ID: {device_info.device_id}")
                print(f"   Device architecture: {device_info.device_architecture}")
            else:
                print(f"   VDevice created successfully (SDK version: HailoRT)")
        except Exception as info_error:
            print(f"   Device info not available (SDK version difference)")

        vdevice = None
        return True

    except ImportError as e:
        print("❌ Hailo SDK not installed")
        print(f"   Error: {e}")
        print("\n   Install with:")
        print("   pip3 install hailort")
        return False

    except Exception as e:
        print("❌ Hailo device not found or SDK error")
        print(f"   Error: {e}")
        print("\n   Troubleshooting:")
        print("   1. Check Hailo HAT+ is properly connected")
        print("   2. Run: lsusb | grep Hailo")
        print("   3. Check drivers: ls /dev/hailo*")
        return False


def test_hef_model():
    """Test HEF model file existence and validity."""
    print("\n" + "="*60)
    print("TEST 2: HEF Model File")
    print("="*60)

    config_path = os.path.join(os.path.dirname(__file__), "config", "detection_config.json")

    if not os.path.exists(config_path):
        print(f"❌ Config file not found: {config_path}")
        return False

    # Load config
    import json
    with open(config_path, 'r') as f:
        config = json.load(f)

    model_path = config.get('model_path', '')

    if not model_path:
        print("❌ model_path not set in config")
        return False

    print(f"Model path from config: {model_path}")

    if not os.path.exists(model_path):
        print(f"❌ HEF file not found: {model_path}")
        print("\n   You need to compile YOLOv8 to HEF format:")
        print("   1. Download YOLOv8s ONNX: https://github.com/ultralytics/assets")
        print("   2. Use Hailo Dataflow Compiler to convert ONNX -> HEF")
        print("   3. Or use pre-compiled HEF from Hailo Model Zoo")
        return False

    # Check file size
    file_size = os.path.getsize(model_path) / (1024 * 1024)  # MB
    print(f"✅ HEF file found")
    print(f"   Size: {file_size:.2f} MB")

    # Check file extension
    if not model_path.endswith('.hef'):
        print(f"⚠️  Warning: File doesn't have .hef extension")

    return True


def test_model_loading():
    """Test loading HEF model into Hailo inference agent."""
    print("\n" + "="*60)
    print("TEST 3: Model Loading")
    print("="*60)

    config_path = os.path.join(os.path.dirname(__file__), "config", "detection_config.json")

    try:
        print("Initializing InferenceAgentHailo...")
        agent = InferenceAgentHailo(config_path)

        print("Loading HEF model...")
        start_time = time.time()

        if agent.load_model():
            load_time = time.time() - start_time
            print(f"✅ Model loaded successfully")
            print(f"   Load time: {load_time:.2f} seconds")

            # Check if model is ready
            if agent.is_ready():
                print(f"✅ Model ready for inference")
            else:
                print(f"❌ Model not ready")
                return False

            agent.unload_model()
            return True

        else:
            print("❌ Failed to load model")
            return False

    except Exception as e:
        print(f"❌ Error during model loading: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_inference_performance():
    """Test inference speed and accuracy."""
    print("\n" + "="*60)
    print("TEST 4: Inference Performance")
    print("="*60)

    config_path = os.path.join(os.path.dirname(__file__), "config", "detection_config.json")

    try:
        # Initialize agent
        agent = InferenceAgentHailo(config_path)

        if not agent.load_model():
            print("❌ Failed to load model")
            return False

        # Create test images
        test_cases = [
            ("640x640 RGB", np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)),
            ("1920x1080 RGB", np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)),
            ("1280x720 RGB", np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)),
        ]

        print("\nRunning inference tests (10 iterations each)...\n")

        for name, test_image in test_cases:
            times = []

            # Warm-up
            _ = agent.detect(test_image)

            # Benchmark
            for _ in range(10):
                start = time.time()
                detections = agent.detect(test_image)
                elapsed = time.time() - start
                times.append(elapsed)

            avg_time = np.mean(times) * 1000  # Convert to ms
            fps = 1000 / avg_time

            print(f"{name}:")
            print(f"  Avg inference time: {avg_time:.2f} ms")
            print(f"  FPS: {fps:.1f}")
            print(f"  Min/Max: {min(times)*1000:.2f}/{max(times)*1000:.2f} ms")

        agent.unload_model()
        print("\n✅ Performance test completed")
        return True

    except Exception as e:
        print(f"❌ Error during performance test: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_detection_with_real_image():
    """Test detection with a real camera frame or sample image."""
    print("\n" + "="*60)
    print("TEST 5: Real Image Detection")
    print("="*60)

    config_path = os.path.join(os.path.dirname(__file__), "config", "detection_config.json")

    try:
        # Try to capture from camera
        print("Attempting to capture frame from camera...")
        cap = cv2.VideoCapture(0)

        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()

            if ret and frame is not None:
                print("✅ Captured frame from camera")
                test_image = frame
            else:
                print("⚠️  Failed to capture, using synthetic image")
                test_image = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
        else:
            print("⚠️  No camera available, using synthetic image")
            test_image = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)

        # Initialize agent
        agent = InferenceAgentHailo(config_path)

        if not agent.load_model():
            print("❌ Failed to load model")
            return False

        # Run detection
        print("Running detection...")
        start = time.time()
        detections = agent.detect(test_image)
        elapsed = time.time() - start

        print(f"\n✅ Detection completed in {elapsed*1000:.2f} ms")
        print(f"   Found {len(detections)} objects")

        if detections:
            print("\n   Detections:")
            for i, det in enumerate(detections[:10], 1):  # Show max 10
                print(f"   {i}. {det['class']} - {det['confidence']:.2%} - bbox: {det['bbox']}")

            if len(detections) > 10:
                print(f"   ... and {len(detections) - 10} more")

        agent.unload_model()
        return True

    except Exception as e:
        print(f"❌ Error during detection test: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all Hailo inference tests."""
    print("\n" + "="*70)
    print(" HAILO-8 INFERENCE TEST SUITE")
    print("="*70)

    results = {}

    # Test 1: SDK and device
    results['hailo_sdk'] = test_hailo_sdk()

    if not results['hailo_sdk']:
        print("\n❌ Cannot proceed without Hailo SDK and device")
        print_summary(results)
        return False

    # Test 2: HEF model
    results['hef_model'] = test_hef_model()

    if not results['hef_model']:
        print("\n❌ Cannot proceed without HEF model")
        print_summary(results)
        return False

    # Test 3: Model loading
    results['model_loading'] = test_model_loading()

    # Test 4: Performance
    if results['model_loading']:
        results['performance'] = test_inference_performance()

    # Test 5: Real detection
    if results['model_loading']:
        results['real_detection'] = test_detection_with_real_image()

    # Summary
    print_summary(results)

    all_passed = all(results.values())
    return all_passed


def print_summary(results):
    """Print test summary."""
    print("\n" + "="*70)
    print(" TEST SUMMARY")
    print("="*70)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:20s} : {status}")

    all_passed = all(results.values())
    print("\n" + "="*70)
    if all_passed:
        print("✅ ALL TESTS PASSED - Hailo-8 is ready for deployment!")
    else:
        print("❌ SOME TESTS FAILED - Check errors above")
    print("="*70 + "\n")


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
