import json
import time
import requests
from requests.adapters import HTTPAdapter
from utils.logger import get_logger

# Robust Retry Import
try:
    from urllib3.util.retry import Retry
except ImportError:
    try:
        from requests.packages.urllib3.util.retry import Retry
    except ImportError:
        # Emergency fallback for missing dependencies
        class Retry:
            def __init__(self, *args, **kwargs): pass

from utils.binding_manager import BindingManager

class TransportAgent:
    def __init__(self, config_path="config/backend_config.json"):
        self.logger = get_logger(self.__class__.__name__)
        self.config = self._load_config(config_path)
        self.binding = BindingManager()
        self.init_time = time.time()
        self.session = self._create_session()

    def _load_config(self, path):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception:
            return {}

    def _create_session(self):
        """Creates a session with initial or bound auth."""
        session = requests.Session()
        retry_strategy = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        session.mount("https://", HTTPAdapter(max_retries=retry_strategy))
        session.mount("http://", HTTPAdapter(max_retries=retry_strategy))
        session.headers.update({"Content-Type": "application/json"})
        return session

    def _update_session_auth(self):
        """Syncs session headers with binding config including custom headers."""
        if self.binding.is_bound():
            config = self.binding.config
            
            # 1. Clear previous dynamic headers
            for h in list(self.session.headers.keys()):
                if h not in ['Content-Type', 'User-Agent']:
                    self.session.headers.pop(h)

            # 2. Add Standard Auth based on auth_mode
            token = config.get("auth_token", "")
            auth_mode = config.get("auth_mode", "bearer").lower()
            
            if auth_mode == "apikey":
                self.session.headers.update({"X-API-Key": token})
            elif auth_mode == "bearer":
                self.session.headers.update({"Authorization": f"Bearer {token}"})
            elif auth_mode == "custom":
                # Expecting custom_auth_header key
                header_key = config.get("custom_auth_header", "Authorization")
                self.session.headers.update({header_key: token})

            # 3. Apply Multi-Backend Custom Headers
            custom = config.get("custom_headers", {})
            if isinstance(custom, dict):
                self.session.headers.update(custom)

    def _post_raw(self, url, data):
        """Low-level POST with dynamic auth application."""
        if not self.binding.is_bound():
            self.logger.debug("Unit UNBOUND. Skipping data transmission.")
            return False

        self._update_session_auth()
        timeout = self.config.get("timeout", 10)
        
        try:
            # Universal POST - works with standard JSON ingestion
            response = self.session.post(url, json=data, timeout=timeout)
            response.raise_for_status()
            return True
        except Exception as e:
            self.logger.error(f"Post to {url} failed: {e}")
            return False

    def send_counts(self, counts_data):
        """Sends counts to any backend endpoint. Supports Legacy (flat) and Universal (nested) formats."""
        if not self.binding.is_bound(): return False
        
        config = self.binding.config
        url = config.get("endpoint")
        format_type = config.get("payload_format", "legacy").lower() # DEFAULT TO LEGACY for dashboard compatibility
        
        if format_type == "legacy":
            # FLAT SCHEMA: Matches your existing Firebase/React Dashboard exactly
            payload = {
                "camera_id": config.get("camera_id"),
                "site_id": config.get("site_id"),
                "timestamp": counts_data.get("timestamp"),
                "counts": counts_data
            }
        elif format_type == "aiod05":
            # AIODCOUNTER05 SCHEMA: Matches Multitenant Site/Camera structure
            payload = {
                "tenant_id": config.get("tenant_id"),
                "site_id": config.get("site_id"),
                "camera_id": config.get("camera_id"),
                "serial": self.binding.serial_number,
                "timestamp": counts_data.get("timestamp"),
                "data": {
                    "counts": counts_data,
                    "event_type": "periodic_report"
                }
            }
        else:
            # UNIVERSAL/NESTED SCHEMA: Professional scalable production format
            payload = {
                "identity": {
                    "serial": self.binding.serial_number,
                    "camera_id": config.get("camera_id"),
                    "site_id": config.get("site_id")
                },
                "environment": {
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "uptime": time.time() - (getattr(self, 'init_time', time.time()))
                },
                "data": {
                    "type": "object_counts",
                    "counts": counts_data
                }
            }
        return self._post_raw(url, payload)

    def send_activation(self, payload=None):
        """Handshake notification (optional based on backend requirements)."""
        if not self.binding.is_bound(): return False
        
        url = self.binding.config.get("endpoint")
        # If no payload provided, send a default one
        if payload is None:
            payload = {"status": "active", "serial": self.binding.serial_number}
        
        # We reuse the ingest endpoint for activation signals unless a separate one is bound
        return self._post_raw(url, payload)

    def send_status(self, status):
        """Periodic status update."""
        return True # Placeholder
