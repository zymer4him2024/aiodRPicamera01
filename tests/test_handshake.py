#!/usr/bin/env python3
"""
Handshake Test Script - Tests RPi <-> Firebase Backend handshake

This script tests the complete handshake flow:
1. Generates a test QR payload (simulating QR scan)
2. Performs handshake with the backend
3. Verifies binding was successful
4. Sends a test count to verify data flow

Usage:
    python3 tests/test_handshake.py --token YOUR_QR_TOKEN

    Or for quick test with simulated token:
    python3 tests/test_handshake.py --simulate
"""

import sys
import os
import argparse
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.handshake_agent import HandshakeAgent
from agents.transport_agent import TransportAgent
from utils.binding_manager import BindingManager


def print_header(text):
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)


def print_status(label, value, is_ok=True):
    status = "✅" if is_ok else "❌"
    print(f"  {status} {label}: {value}")


def test_handshake(args):
    """Main test function."""
    print_header("RPi-Backend Handshake Test")
    
    # 1. Check current binding status
    print("\n📋 Current Device Status:")
    bm = BindingManager()
    info = bm.get_info()
    print_status("Serial Number", info["serial"])
    print_status("Currently Bound", "Yes" if info["bound"] else "No", info["bound"])
    
    if info["bound"] and not args.force:
        print("\n⚠️  Device is already bound. Use --force to rebind or --reset to unbind first.")
        return False
    
    # 2. Prepare QR payload
    print_header("Preparing QR Payload")
    
    if args.simulate:
        # For simulation, we need a valid token from the backend
        # This is a placeholder - in real use, copy the token from the dashboard
        print("  ⚠️  SIMULATION MODE")
        print("  To test with real backend, you need to:")
        print("  1. Generate a token using the admin dashboard or curl command")
        print("  2. Run: python3 tests/test_handshake.py --token YOUR_TOKEN --backend-url YOUR_URL")
        
        # Show example curl command
        print("\n  📝 To generate a token manually, run:")
        print("  curl -X POST 'https://us-central1-aiodcounter06.cloudfunctions.net/api/admin/sites/generate-token' \\")
        print("    -H 'Authorization: Bearer YOUR_FIREBASE_TOKEN' \\")
        print("    -H 'Content-Type: application/json' \\")
        print("    -d '{\"site_id\":\"global-innovation-anaheim-001\",\"org_id\":\"global-innovation\"}'")
        return False
    
    if not args.token:
        print("  ❌ No token provided. Use --token YOUR_TOKEN")
        return False
    
    # Build QR payload
    qr_payload = {
        "backend_url": args.backend_url,
        "token": args.token,
        "site_id": args.site_id or "from-qr"
    }
    
    print_status("Backend URL", qr_payload["backend_url"])
    print_status("Token", f"{qr_payload['token'][:16]}..." if len(qr_payload['token']) > 16 else qr_payload['token'])
    
    # 3. Perform handshake
    print_header("Performing Handshake")
    
    handshake = HandshakeAgent()
    
    if args.reset:
        print("  🔄 Resetting device to factory state...")
        handshake.reset()
    
    success = handshake.perform_handshake(qr_payload)
    
    if success:
        print_status("Handshake Result", "SUCCESS", True)
    else:
        print_status("Handshake Result", "FAILED", False)
        return False
    
    # 4. Verify binding
    print_header("Verifying Binding")
    
    bm = BindingManager()  # Reload
    info = bm.get_info()
    
    print_status("Bound", "Yes" if info["bound"] else "No", info["bound"])
    print_status("Camera ID", info.get("camera_id", "N/A"))
    print_status("Site ID", info.get("site_id", "N/A"))
    print_status("Endpoint", info.get("endpoint", "N/A"))
    
    # 5. Test data transmission
    if args.test_data:
        print_header("Testing Data Transmission")
        
        transport = TransportAgent()
        
        test_counts = {
            "Pedestrians": 10,
            "Cars": 5,
            "Buses": 1,
            "Trucks": 2,
            "Motorcycles": 3,
            "total": 21,
            "timestamp": "2026-01-14T12:00:00Z"
        }
        
        print("  📤 Sending test counts to backend...")
        result = transport.send_counts(test_counts)
        print_status("Data Transmission", "SUCCESS" if result else "FAILED", result)
    
    # 6. Summary
    print_header("Test Summary")
    print("  ✅ Handshake completed successfully!")
    print(f"  📍 Device bound to: {info.get('site_id', 'Unknown')}")
    print(f"  🔗 Sending data to: {info.get('endpoint', 'Unknown')}")
    
    return True


def main():
    parser = argparse.ArgumentParser(description="Test RPi-Backend Handshake")
    
    parser.add_argument(
        "--token",
        help="QR registration token from backend"
    )
    parser.add_argument(
        "--backend-url",
        default="https://us-central1-aiodcounter06.cloudfunctions.net/api",
        help="Backend API URL"
    )
    parser.add_argument(
        "--site-id",
        help="Site ID (optional, backend will determine from token)"
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Simulation mode - shows instructions only"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force rebind even if already bound"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset device to unbound state before handshake"
    )
    parser.add_argument(
        "--test-data",
        action="store_true",
        help="Send test data after handshake"
    )
    
    args = parser.parse_args()
    
    try:
        success = test_handshake(args)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
