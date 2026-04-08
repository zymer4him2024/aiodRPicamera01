"""
HandshakeAgent - Handles device self-registration with backend

Responsibilities:
- Processes QR payload (from file or direct input)
- Registers device with Firebase backend
- Stores binding configuration locally
- Manages device identity and credentials

This agent is standalone and works independently of the backend.
"""
import json
import requests
import time
import os
from utils.logger import get_logger
from utils.binding_manager import BindingManager


class HandshakeAgent:
    """
    Manages the QR-based handshake flow between RPi and Firebase backend.
    
    Flow:
    1. Load QR payload (contains token, backend URL)
    2. Send registration request to backend
    3. Receive binding configuration
    4. Store in local binding.json
    5. Send activation ping
    """
    
    def __init__(self, qr_payload_path="config/qr_payload.json", binding_manager=None):
        self.logger = get_logger(self.__class__.__name__)
        self.qr_payload_path = qr_payload_path
        self.binding_manager = binding_manager if binding_manager else BindingManager()
        
    def load_qr_payload(self):
        """Loads QR payload from file (simulates scanning QR)."""
        if not os.path.exists(self.qr_payload_path):
            self.logger.info("No QR payload found. Device is standalone.")
            return None
            
        try:
            with open(self.qr_payload_path, 'r') as f:
                payload = json.load(f)
                self.logger.info(f"Loaded QR payload for site: {payload.get('site_id', 'unknown')}")
                return payload
        except Exception as e:
            self.logger.error(f"Failed to load QR payload: {e}")
            return None
    
    def save_qr_payload(self, payload):
        """Saves QR payload to file (for testing/simulation)."""
        try:
            os.makedirs(os.path.dirname(self.qr_payload_path), exist_ok=True)
            with open(self.qr_payload_path, 'w') as f:
                json.dump(payload, f, indent=4)
            self.logger.info(f"QR payload saved to {self.qr_payload_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save QR payload: {e}")
            return False
    
    def register_with_backend(self, qr_payload):
        """
        Sends registration request to backend using QR token.
        
        Args:
            qr_payload: Dict containing:
                - backend_url: Base URL of the Firebase backend
                - token: One-time registration token from QR
                - site_id: Target site ID
                
        Returns:
            Binding configuration on success, None on failure
        """
        backend_url = qr_payload.get("backend_url")
        token = qr_payload.get("token")
        
        if not backend_url or not token:
            self.logger.error("Invalid QR payload: missing backend_url or token")
            return None
        
        # Get device serial
        serial = self.binding_manager.serial_number
        
        registration_url = f"{backend_url}/device/register"
        
        request_body = {
            "serial": serial,
            "token": token,
            "ip": self._get_local_ip(),
            "firmware_version": "1.0.0"
        }
        
        self.logger.info(f"Registering device {serial} with backend...")
        self.logger.info(f"Registration URL: {registration_url}")
        
        try:
            response = requests.post(
                registration_url,
                json=request_body,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    self.logger.info("Registration successful!")
                    return result.get("binding")
                else:
                    self.logger.error(f"Registration rejected: {result.get('error')}")
                    return None
            else:
                self.logger.error(f"Registration failed with status {response.status_code}: {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            self.logger.error("Registration request timed out")
            return None
        except requests.exceptions.ConnectionError as e:
            self.logger.error(f"Cannot reach backend: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Registration error: {e}")
            return None
    
    def perform_handshake(self, qr_payload=None):
        """
        Performs the complete handshake flow.
        
        Args:
            qr_payload: Optional QR payload dict. If None, loads from file.
            
        Returns:
            True if handshake successful, False otherwise
        """
        # 1. Load or use provided QR payload
        if qr_payload is None:
            qr_payload = self.load_qr_payload()
        
        if qr_payload is None:
            self.logger.warning("No QR payload available. Cannot perform handshake.")
            return False
        
        # 2. Check if already bound
        if self.binding_manager.is_bound():
            self.logger.info("Device is already bound. Use reset() to unbind first.")
            return True  # Already in good state
        
        # 3. Register with backend
        binding_config = self.register_with_backend(qr_payload)
        
        if binding_config is None:
            self.logger.error("Handshake failed: Could not get binding from backend")
            return False
        
        # 4. Store binding configuration
        if not self.binding_manager.bind(binding_config):
            self.logger.error("Handshake failed: Could not save binding locally")
            return False
        
        # 5. Send activation ping
        if not self._send_activation_ping(binding_config):
            self.logger.warning("Activation ping failed, but device is bound")
            # Don't fail the handshake for this
        
        # 6. Clean up QR payload file (one-time use)
        self._cleanup_qr_payload()
        
        self.logger.info("==========================================")
        self.logger.info("    HANDSHAKE COMPLETE - DEVICE BOUND     ")
        self.logger.info(f"    Camera ID: {binding_config.get('camera_id')}")
        self.logger.info(f"    Site: {binding_config.get('site_name')}")
        self.logger.info("==========================================")
        
        return True
    
    def _send_activation_ping(self, binding_config):
        """Sends activation confirmation to backend."""
        endpoint = binding_config.get("endpoint", "")
        
        # Construct activation URL from ingest endpoint
        # /ingestCounts -> /api/device/activate
        base_url = endpoint.rsplit('/', 1)[0] if endpoint else ""
        activation_url = f"{base_url}/api/device/activate"
        
        # Alternative: use direct activation endpoint
        if "cloudfunctions.net" in endpoint:
            # For Firebase functions, use the api function
            parts = endpoint.split("/")
            activation_url = "/".join(parts[:-1]) + "/api/device/activate"
        
        try:
            response = requests.post(
                activation_url,
                json={
                    "serial": self.binding_manager.serial_number,
                    "status": "active"
                },
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                self.logger.info("Activation ping successful")
                return True
            else:
                self.logger.warning(f"Activation ping returned {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.warning(f"Activation ping failed: {e}")
            return False
    
    def _cleanup_qr_payload(self):
        """Removes QR payload file after successful registration."""
        try:
            if os.path.exists(self.qr_payload_path):
                os.remove(self.qr_payload_path)
                self.logger.info("QR payload file cleaned up")
        except Exception as e:
            self.logger.warning(f"Could not clean up QR payload: {e}")
    
    def _get_local_ip(self):
        """Gets the device's local IP address."""
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "unknown"
    
    def reset(self):
        """Factory reset - unbinds device."""
        self.binding_manager.unbind()
        self._cleanup_qr_payload()
        self.logger.info("Device reset to factory state (UNBOUND)")
    
    def get_status(self):
        """Returns current handshake/binding status."""
        return {
            "serial": self.binding_manager.serial_number,
            "bound": self.binding_manager.is_bound(),
            "qr_payload_present": os.path.exists(self.qr_payload_path),
            **self.binding_manager.get_info()
        }


# Convenience function for testing
def perform_handshake_from_qr(qr_data):
    """
    Convenience function to perform handshake from QR data.
    
    Args:
        qr_data: Can be a dict or JSON string containing QR payload
        
    Returns:
        True if successful, False otherwise
    """
    agent = HandshakeAgent()
    
    if isinstance(qr_data, str):
        try:
            qr_data = json.loads(qr_data)
        except json.JSONDecodeError:
            print("Invalid QR data: not valid JSON")
            return False
    
    return agent.perform_handshake(qr_data)
