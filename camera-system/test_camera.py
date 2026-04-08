#!/usr/bin/env python3
"""
Test script for camera functionality.
Tests camera connection, frame capture, and configuration.
"""

import sys
import os
import cv2
import time

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.camera_agent import CameraAgent
from utils.logger import setup_logger


def test_camera_connection():
    """Test camera device detection."""
    print("\n" + "="*60)
    print("TEST 1: Camera Device Detection")
    print("="*60)

    # Check for video devices
    devices = []
    for i in range(10):
        device_path = f"/dev/video{i}"
        if os.path.exists(device_path):
            devices.append(i)

    if devices:
        print(f"✅ Found video devices: {devices}")
        return devices[0]
    else:
        print("❌ No video devices found")
        print("   Run: ls -la /dev/video*")
        return None


def test_camera_capture(device_id=0):
    """Test direct camera capture using OpenCV."""
    print("\n" + "="*60)
    print(f"TEST 2: Direct Camera Capture (device {device_id})")
    print("="*60)

    try:
        cap = cv2.VideoCapture(device_id)

        if not cap.isOpened():
            print(f"❌ Failed to open camera device {device_id}")
            return False

        # Try to read a frame
        ret, frame = cap.read()

        if ret and frame is not None:
            h, w, c = frame.shape
            print(f"✅ Successfully captured frame")
            print(f"   Resolution: {w}x{h}")
            print(f"   Channels: {c}")
            print(f"   Data type: {frame.dtype}")
            print(f"   Shape: {frame.shape}")

            # Save test image
            output_path = "/tmp/test_frame.jpg"
            cv2.imwrite(output_path, frame)
            print(f"   Saved test frame to: {output_path}")

            cap.release()
            return True
        else:
            print("❌ Failed to capture frame")
            cap.release()
            return False

    except Exception as e:
        print(f"❌ Error during capture: {e}")
        return False


def test_camera_agent():
    """Test CameraAgent class."""
    print("\n" + "="*60)
    print("TEST 3: CameraAgent Class")
    print("="*60)

    config_path = os.path.join(os.path.dirname(__file__), "config", "camera_config.json")

    if not os.path.exists(config_path):
        print(f"❌ Config file not found: {config_path}")
        return False

    try:
        # Initialize agent
        print("Initializing CameraAgent...")
        agent = CameraAgent(config_path)

        # Start camera
        print("Starting camera...")
        if not agent.start():
            print("❌ Failed to start camera")
            return False

        print("✅ Camera started successfully")

        # Wait for camera to initialize
        time.sleep(2)

        # Capture frames
        print("\nCapturing 5 test frames...")
        for i in range(5):
            frame = agent.get_frame()
            if frame is not None:
                h, w, c = frame.shape
                print(f"  Frame {i+1}: {w}x{h}x{c} ✅")
            else:
                print(f"  Frame {i+1}: Failed ❌")
            time.sleep(0.5)

        # Stop camera
        print("\nStopping camera...")
        agent.stop()
        print("✅ Camera agent test completed")

        return True

    except Exception as e:
        print(f"❌ Error during CameraAgent test: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_camera_settings():
    """Test different camera settings."""
    print("\n" + "="*60)
    print("TEST 4: Camera Settings")
    print("="*60)

    device_id = 0
    resolutions = [
        (640, 480),
        (1280, 720),
        (1920, 1080)
    ]

    for width, height in resolutions:
        print(f"\nTesting resolution: {width}x{height}")
        try:
            cap = cv2.VideoCapture(device_id)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

            ret, frame = cap.read()
            if ret and frame is not None:
                actual_w, actual_h = frame.shape[1], frame.shape[0]
                if actual_w == width and actual_h == height:
                    print(f"  ✅ {width}x{height} supported")
                else:
                    print(f"  ⚠️  Requested {width}x{height}, got {actual_w}x{actual_h}")
            else:
                print(f"  ❌ {width}x{height} failed")

            cap.release()

        except Exception as e:
            print(f"  ❌ Error: {e}")

    return True


def main():
    """Run all camera tests."""
    print("\n" + "="*70)
    print(" CAMERA SYSTEM TEST SUITE")
    print("="*70)

    results = {}

    # Test 1: Device detection
    device_id = test_camera_connection()
    results['device_detection'] = device_id is not None

    if device_id is None:
        print("\n❌ Cannot proceed without camera device")
        return False

    # Test 2: Direct capture
    results['direct_capture'] = test_camera_capture(device_id)

    # Test 3: Camera agent
    results['camera_agent'] = test_camera_agent()

    # Test 4: Settings
    results['camera_settings'] = test_camera_settings()

    # Summary
    print("\n" + "="*70)
    print(" TEST SUMMARY")
    print("="*70)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:20s} : {status}")

    all_passed = all(results.values())
    print("\n" + "="*70)
    if all_passed:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("="*70 + "\n")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
