import json
import time
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from utils.logger import get_logger

class TransportAgent:
    def __init__(self, config_path="config/backend_config.json"):
        self.logger = get_logger(self.__class__.__name__)
        self.config = self._load_config(config_path)
        self.session = self._create_session()

    def _load_config(self, path):
        try:
            with open(path, 'r') as f:
                config = json.load(f)
                self.logger.info(f"Loaded backend config from {path}")
                return config
        except FileNotFoundError:
            self.logger.error(f"Config file not found: {path}")
            raise
        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON in config file: {path}")
            raise

    def _create_session(self):
        """
        Creates a requests session with retry logic and exponential backoff.
        """
        session = requests.Session()
        retries = self.config.get("max_retries", 10)
        
        retry_strategy = Retry(
            total=retries,
            backoff_factor=1, # Exponential backoff: {backoff factor} * (2 ** ({number of total retries} - 1))
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        # Auth Handling based on config
        auth_type = self.config.get("auth_type", "Bearer")
        token = self.config.get("auth_token", "")
        
        if auth_type == "X-API-Key":
            session.headers.update({"X-API-Key": token})
        else:
            session.headers.update({"Authorization": f"Bearer {token}"})
            
        session.headers.update({"Content-Type": "application/json"})
        
        return session

    def _post(self, endpoint_key, data):
        """
        Helper to send POST requests.
        """
        base_url = self.config.get("api_base_url", "")
        endpoint = self.config.get("endpoints", {}).get(endpoint_key, "")
        
        if not base_url or not endpoint:
            self.logger.error(f"Invalid URL configuration for {endpoint_key}")
            return False

        url = f"{base_url}{endpoint}"
        timeout = self.config.get("timeout", 10)

        try:
            response = self.session.post(url, json=data, timeout=timeout)
            response.raise_for_status()
            self.logger.info(f"Successfully sent data to {endpoint_key}")
            return True
        except requests.exceptions.HTTPError as errh:
            self.logger.error(f"Http Error: {errh}")
        except requests.exceptions.ConnectionError as errc:
            self.logger.error(f"Error Connecting: {errc}")
        except requests.exceptions.Timeout as errt:
            self.logger.error(f"Timeout Error: {errt}")
        except requests.exceptions.RequestException as err:
            self.logger.error(f"OOps: Something Else: {err}")
        return False

    def send_counts(self, counts_data):
        """
        Sends count data to the backend.
        """
        payload = {
            "camera_id": self.config.get("camera_id"),
            "site_id": self.config.get("site_id"),
            "timestamp": counts_data.get("timestamp"),
            "counts": counts_data
        }
        # Remove metadata from counts dict if it was passed directly, 
        # or assume counts_data is just the counts. 
        # Based on previous prompt, counts_data has timestamp and total.
        # Let's adjust payload structure to match requirement "Include camera_id, site_id, timestamp, counts".
        # If counts_data already has timestamp, we use it.
        
        return self._post("counts", payload)

    def send_activation(self, camera_info):
        """
        Sends activation request.
        """
        payload = {
            "camera_id": self.config.get("camera_id"),
            "site_id": self.config.get("site_id"),
            "status": camera_info.get("status"),
            "activated_at": camera_info.get("activated_at")
        }
        return self._post("activate", payload)

    def send_status(self, status_info):
        """
        Sends status updates.
        """
        payload = {
            "camera_id": self.config.get("camera_id"),
            "status": status_info
        }
        return self._post("status", payload)
