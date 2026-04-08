#!/usr/bin/env python3
"""
End-to-end test script for complete camera detection pipeline.
Tests camera -> inference -> counting -> transport flow.
"""

import sys
import os
import time
import json

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.camera_agent import CameraAgent
from agents.inference_agent_hailo import InferenceAgentHailo
from agents.counting_agent import CountingAgent
from agents.transport_agent import TransportAgent
from utils.logger import setup_logger


def test_pipeline_integration():
    """Test full pipeline: camera -> inference -> counting."""
    print("\n" + "="*60)
    print("TEST 1: Pipeline Integration (Camera -> Inference -> Counting)")
    print("="*60)

    # Config paths
    camera_config = os.path.join(os.path.dirname(__file__), "config", "camera_config.json")
    detection_config = os.path.join(os.path.dirname(__file__), "config", "detection_config.json")
    counting_config = os.path.join(os.path.dirname(__file__), "config", "counting_config.json")

    try:
        # Initialize agents
        print("\n1. Initializing agents...")
        camera = CameraAgent(camera_config)
        inference = InferenceAgentHailo(detection_config)
        counting = CountingAgent(counting_config)

        # Start camera
        print("2. Starting camera...")
        if not camera.start():
            print("❌ Failed to start camera")
            return False
        print("✅ Camera started")

        # Load model
        print("3. Loading Hailo model...")
        if not inference.load_model():
            print("❌ Failed to load model")
            camera.stop()
            return False
        print("✅ Model loaded")

        # Wait for camera to stabilize
        time.sleep(2)

        # Run pipeline for 10 frames
        print("\n4. Running detection pipeline (10 frames)...\n")

        detection_counts = []
        total_inference_time = 0
        successful_frames = 0

        for i in range(10):
            # Get frame
            frame = camera.get_frame()

            if frame is None:
                print(f"   Frame {i+1:2d}: ❌ No frame")
                continue

            # Run inference
            start = time.time()
            detections = inference.detect(frame)
            inference_time = (time.time() - start) * 1000

            total_inference_time += inference_time

            # Count objects
            counts = counting.process_detections(detections)

            detection_counts.append(len(detections))
            successful_frames += 1

            # Display results
            total = counts.get('total', 0)
            print(f"   Frame {i+1:2d}: {total:2d} objects detected in {inference_time:6.2f}ms - {counts}")

            time.sleep(0.5)

        # Calculate stats
        print("\n5. Statistics:")
        if successful_frames > 0:
            avg_detections = sum(detection_counts) / len(detection_counts)
            avg_inference = total_inference_time / successful_frames
            fps = 1000 / avg_inference

            print(f"   Successful frames: {successful_frames}/10")
            print(f"   Avg detections per frame: {avg_detections:.1f}")
            print(f"   Avg inference time: {avg_inference:.2f} ms")
            print(f"   Theoretical FPS: {fps:.1f}")
        else:
            print("   ❌ No successful frames")

        # Cleanup
        print("\n6. Cleaning up...")
        inference.unload_model()
        camera.stop()
        print("✅ Pipeline test completed")

        return successful_frames > 0

    except Exception as e:
        print(f"❌ Error during pipeline test: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_transport_agent():
    """Test transport agent Firebase communication."""
    print("\n" + "="*60)
    print("TEST 2: Transport Agent (Firebase Communication)")
    print("="*60)

    backend_config = os.path.join(os.path.dirname(__file__), "config", "backend_config.json")

    # Check if Firebase is configured
    with open(backend_config, 'r') as f:
        config = json.load(f)

    if not config.get('camera_id') or not config.get('auth_token'):
        print("⚠️  Firebase not configured - skipping transport test")
        print("   To test transport:")
        print("   1. Edit config/backend_config.json")
        print("   2. Add camera_id, site_id, auth_token, and endpoints")
        return True  # Not a failure, just skipped

    try:
        print("Firebase configuration found")
        print(f"  Camera ID: {config.get('camera_id')}")
        print(f"  Site ID: {config.get('site_id')}")
        print(f"  Endpoints configured: {bool(config.get('endpoints', {}).get('counts'))}")

        transport = TransportAgent(backend_config)

        # Test sending counts
        print("\nSending test counts to Firebase...")
        test_counts = {
            'person': 5,
            'car': 2,
            'truck': 1,
            'total': 8,
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        }

        success = transport.send_counts(test_counts)

        if success:
            print("✅ Successfully sent counts to Firebase")
            return True
        else:
            print("❌ Failed to send counts to Firebase")
            print("   Check logs/transport.log for details")
            return False

    except Exception as e:
        print(f"❌ Error during transport test: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_full_pipeline_with_transport():
    """Test complete end-to-end pipeline including Firebase upload."""
    print("\n" + "="*60)
    print("TEST 3: Full Pipeline with Transport")
    print("="*60)

    # Config paths
    camera_config = os.path.join(os.path.dirname(__file__), "config", "camera_config.json")
    detection_config = os.path.join(os.path.dirname(__file__), "config", "detection_config.json")
    counting_config = os.path.join(os.path.dirname(__file__), "config", "counting_config.json")
    backend_config = os.path.join(os.path.dirname(__file__), "config", "backend_config.json")

    # Check if Firebase is configured
    with open(backend_config, 'r') as f:
        config = json.load(f)

    if not config.get('camera_id') or not config.get('auth_token'):
        print("⚠️  Firebase not configured - skipping full pipeline test")
        return True  # Not a failure, just skipped

    try:
        # Initialize all agents
        print("\n1. Initializing all agents...")
        camera = CameraAgent(camera_config)
        inference = InferenceAgentHailo(detection_config)
        counting = CountingAgent(counting_config)
        transport = TransportAgent(backend_config)

        # Start camera
        print("2. Starting camera...")
        if not camera.start():
            print("❌ Failed to start camera")
            return False

        # Load model
        print("3. Loading model...")
        if not inference.load_model():
            print("❌ Failed to load model")
            camera.stop()
            return False

        time.sleep(2)

        # Run complete pipeline for 5 iterations
        print("\n4. Running full pipeline (5 iterations)...\n")

        for i in range(5):
            print(f"Iteration {i+1}:")

            # Get frame
            frame = camera.get_frame()
            if frame is None:
                print("  ❌ No frame")
                continue

            # Detect
            detections = inference.detect(frame)
            print(f"  Detected: {len(detections)} objects")

            # Count
            counts = counting.process_detections(detections)
            print(f"  Counts: {counts}")

            # Send to Firebase
            success = transport.send_counts(counts)
            if success:
                print(f"  ✅ Sent to Firebase")
            else:
                print(f"  ❌ Failed to send to Firebase")

            time.sleep(2)

        # Cleanup
        print("\n5. Cleaning up...")
        inference.unload_model()
        camera.stop()
        print("✅ Full pipeline test completed")

        return True

    except Exception as e:
        print(f"❌ Error during full pipeline test: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_performance_metrics():
    """Test and report detailed performance metrics."""
    print("\n" + "="*60)
    print("TEST 4: Performance Metrics")
    print("="*60)

    camera_config = os.path.join(os.path.dirname(__file__), "config", "camera_config.json")
    detection_config = os.path.join(os.path.dirname(__file__), "config", "detection_config.json")
    counting_config = os.path.join(os.path.dirname(__file__), "config", "counting_config.json")

    try:
        # Initialize agents
        camera = CameraAgent(camera_config)
        inference = InferenceAgentHailo(detection_config)
        counting = CountingAgent(counting_config)

        camera.start()
        inference.load_model()
        time.sleep(2)

        # Collect metrics
        metrics = {
            'frame_capture_times': [],
            'inference_times': [],
            'counting_times': [],
            'total_pipeline_times': [],
        }

        print("\nCollecting performance data (20 iterations)...\n")

        for i in range(20):
            start_total = time.time()

            # Frame capture
            start = time.time()
            frame = camera.get_frame()
            metrics['frame_capture_times'].append((time.time() - start) * 1000)

            if frame is None:
                continue

            # Inference
            start = time.time()
            detections = inference.detect(frame)
            metrics['inference_times'].append((time.time() - start) * 1000)

            # Counting
            start = time.time()
            counts = counting.process_detections(detections)
            metrics['counting_times'].append((time.time() - start) * 1000)

            # Total pipeline
            metrics['total_pipeline_times'].append((time.time() - start_total) * 1000)

            if (i + 1) % 5 == 0:
                print(f"  Progress: {i+1}/20")

        # Calculate statistics
        import numpy as np

        print("\n" + "="*60)
        print("PERFORMANCE RESULTS")
        print("="*60)

        for metric_name, times in metrics.items():
            if times:
                avg = np.mean(times)
                std = np.std(times)
                min_time = np.min(times)
                max_time = np.max(times)

                print(f"\n{metric_name.replace('_', ' ').title()}:")
                print(f"  Average: {avg:.2f} ms")
                print(f"  Std Dev: {std:.2f} ms")
                print(f"  Min/Max: {min_time:.2f} / {max_time:.2f} ms")

        # Calculate FPS
        if metrics['total_pipeline_times']:
            avg_total = np.mean(metrics['total_pipeline_times'])
            fps = 1000 / avg_total
            print(f"\nEstimated FPS: {fps:.1f}")

        # Cleanup
        inference.unload_model()
        camera.stop()

        return True

    except Exception as e:
        print(f"❌ Error during performance test: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all end-to-end tests."""
    print("\n" + "="*70)
    print(" END-TO-END PIPELINE TEST SUITE")
    print("="*70)

    results = {}

    # Test 1: Pipeline integration
    results['pipeline_integration'] = test_pipeline_integration()

    # Test 2: Transport agent
    results['transport'] = test_transport_agent()

    # Test 3: Full pipeline with transport
    if results['pipeline_integration'] and results['transport']:
        results['full_pipeline'] = test_full_pipeline_with_transport()

    # Test 4: Performance metrics
    if results['pipeline_integration']:
        results['performance'] = test_performance_metrics()

    # Summary
    print("\n" + "="*70)
    print(" TEST SUMMARY")
    print("="*70)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:25s} : {status}")

    all_passed = all(results.values())
    print("\n" + "="*70)
    if all_passed:
        print("✅ ALL TESTS PASSED - System ready for production!")
    else:
        print("❌ SOME TESTS FAILED - Review errors above")
    print("="*70 + "\n")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
