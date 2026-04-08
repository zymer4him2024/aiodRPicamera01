import sys
import os
import json
import unittest
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.transport_agent import TransportAgent
from utils.binding_manager import BindingManager

class TestAIOD05Integration(unittest.TestCase):
    def setUp(self):
        # Use a temporary binding file for testing
        self.test_binding_file = "config/test_binding.json"
        if os.path.exists(self.test_binding_file):
            os.remove(self.test_binding_file)
        
        self.binding_manager = BindingManager(binding_path=self.test_binding_file)
        self.transport = TransportAgent()
        self.transport.binding = self.binding_manager

    def tearDown(self):
        if os.path.exists(self.test_binding_file):
            os.remove(self.test_binding_file)

    @patch('requests.Session.post')
    def test_aiod05_payload_format(self, mock_post):
        # Configure mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        # 1. Bind with aiod05 format
        bind_data = {
            "endpoint": "https://api.aiodcounter05.com/ingest",
            "auth_token": "test_token_123",
            "payload_format": "aiod05",
            "tenant_id": "TENANT_GOLD_01",
            "site_id": "SITE_PARKING_A",
            "camera_id": "CAM_01"
        }
        self.binding_manager.bind(bind_data)

        # 2. Mock counts data
        counts_data = {
            "person": 5,
            "car": 12,
            "timestamp": "2026-01-12T20:00:00Z"
        }

        # 3. Trigger send_counts
        self.transport.send_counts(counts_data)

        # 4. Verify Payload
        self.assertTrue(mock_post.called)
        args, kwargs = mock_post.call_args
        payload = kwargs.get('json')

        print("\n--- AIOD05 PAYLOAD VERIFICATION ---")
        print(json.dumps(payload, indent=2))

        # Check structure
        self.assertEqual(payload["tenant_id"], "TENANT_GOLD_01")
        self.assertEqual(payload["site_id"], "SITE_PARKING_A")
        self.assertEqual(payload["camera_id"], "CAM_01")
        self.assertEqual(payload["data"]["counts"]["person"], 5)
        self.assertEqual(payload["data"]["event_type"], "periodic_report")
        self.assertIn("HAILO-", payload["serial"])

    @patch('requests.Session.post')
    def test_legacy_payload_format(self, mock_post):
        # 1. Bind with legacy format
        bind_data = {
            "endpoint": "https://legacy-api.com/ingest",
            "auth_token": "legacy_token",
            "payload_format": "legacy",
            "camera_id": "LEGACY_CAM",
            "site_id": "LEGACY_SITE"
        }
        self.binding_manager.bind(bind_data)

        # 2. Trigger send_counts
        self.transport.send_counts({"person": 1, "timestamp": "2026-01-12T20:01:00Z"})

        # 3. Verify Payload
        payload = mock_post.call_args[1].get('json')
        print("\n--- LEGACY PAYLOAD VERIFICATION ---")
        print(json.dumps(payload, indent=2))

        self.assertEqual(payload["camera_id"], "LEGACY_CAM")
        self.assertEqual(payload["counts"]["person"], 1)
        self.assertNotIn("tenant_id", payload)

if __name__ == '__main__':
    unittest.main()
