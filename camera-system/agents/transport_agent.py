import requests
import time
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config_loader import load_config
from utils.logger import setup_logger


class TransportAgent:
    """Handles communication with Firebase Cloud Functions backend."""

    def __init__(self, config_path):
        """Initialize transport agent with backend configuration.

        Args:
            config_path: Path to backend configuration JSON file

        Raises:
            ValueError: If endpoints don't use HTTPS
        """
        self.config = load_config(config_path)
        self.logger = setup_logger('TransportAgent', '/home/digioptics_od/camera-system/logs/transport.log')

        # Extract config values
        self.camera_id = self.config.get('camera_id', '')
        self.site_id = self.config.get('site_id', '')
        self.endpoints = self.config.get('endpoints', {})
        self.auth_token = self.config.get('auth_token', '')
        self.report_interval = self.config.get('report_interval', 15)
        self.retry_attempts = self.config.get('retry_attempts', 3)
        self.timeout = self.config.get('timeout', 10)

        self.logger.info(f"TransportAgent initialized for camera={self.camera_id}, "
                        f"site={self.site_id}, interval={self.report_interval}s")

        # Validate HTTPS enforcement
        self._validate_endpoints()

    def _validate_endpoints(self):
        """Ensure all configured endpoints use HTTPS for security.

        Raises:
            ValueError: If any endpoint uses HTTP instead of HTTPS
        """
        for key, url in self.endpoints.items():
            if url and not url.startswith('https://'):
                self.logger.error(f"Endpoint '{key}' must use HTTPS: {url}")
                raise ValueError(f"Insecure endpoint '{key}': {url}. HTTPS required.")

        self.logger.info("All endpoints validated for HTTPS")

    def send_counts(self, counts_data):
        """Send object counts to Firebase ingestCounts endpoint.

        Args:
            counts_data: Counts dictionary from CountingAgent
                Format: {
                    'person': 10,
                    'car': 5,
                    'timestamp': '2025-01-09T18:30:00Z',
                    'total': 15
                }

        Returns:
            bool: True if send successful, False otherwise

        Firebase payload format:
            {
                'siteId': 'SITE_001',
                'cameraId': 'CAM_001',
                'ts': '2025-01-09T18:30:00Z',
                'windowSec': 15,
                'counts': {'person': 10, 'car': 5},
                'total': 15
            }
        """
        endpoint = self.endpoints.get('counts', '')

        if not endpoint:
            self.logger.warning("No counts endpoint configured, skipping send")
            return True  # Not a failure if endpoint not configured

        # Build Firebase-compatible payload
        payload = {
            'siteId': self.site_id,
            'cameraId': self.camera_id,
            'ts': counts_data.get('timestamp', ''),
            'windowSec': self.report_interval,
            'counts': {k: v for k, v in counts_data.items() if k not in ['timestamp', 'total']},
            'total': counts_data.get('total', 0)
        }

        headers = {
            'Content-Type': 'application/json',
            'X-API-Key': self.auth_token
        }

        self.logger.debug(f"Sending counts payload: {payload}")
        return self._send_with_retry(endpoint, payload, headers, 'counts')

    def send_activation(self, camera_info):
        """Send camera activation request to Firebase (if endpoint exists).

        Args:
            camera_info: Dictionary with camera activation info
                Format: {'timestamp': '2025-01-09T18:30:00Z', ...}

        Returns:
            bool: True if send successful or endpoint not configured, False otherwise
        """
        endpoint = self.endpoints.get('activate', '')

        if not endpoint:
            self.logger.info("No activation endpoint configured, skipping")
            return True

        payload = {
            'cameraId': self.camera_id,
            'siteId': self.site_id,
            'status': 'active',
            'activated_at': camera_info.get('timestamp', '')
        }

        headers = {
            'Content-Type': 'application/json',
            'X-API-Key': self.auth_token
        }

        return self._send_with_retry(endpoint, payload, headers, 'activation')

    def send_status(self, status_info):
        """Send camera status update to Firebase (if endpoint exists).

        Args:
            status_info: Dictionary with status information
                Format: {'status': 'running', 'timestamp': '2025-01-09T18:30:00Z'}

        Returns:
            bool: True if send successful or endpoint not configured, False otherwise
        """
        endpoint = self.endpoints.get('status', '')

        if not endpoint:
            self.logger.info("No status endpoint configured, skipping")
            return True

        payload = {
            'cameraId': self.camera_id,
            'siteId': self.site_id,
            'status': status_info.get('status', 'unknown'),
            'timestamp': status_info.get('timestamp', '')
        }

        headers = {
            'Content-Type': 'application/json',
            'X-API-Key': self.auth_token
        }

        return self._send_with_retry(endpoint, payload, headers, 'status')

    def _send_with_retry(self, endpoint, payload, headers, request_type):
        """Send HTTP POST with exponential backoff retry logic.

        Args:
            endpoint: Target URL
            payload: JSON payload dictionary
            headers: HTTP headers dictionary
            request_type: Type of request for logging ('counts', 'activation', 'status')

        Returns:
            bool: True if request succeeded (200 OK), False otherwise

        Retry logic:
            - 4xx errors (client fault): Don't retry, return False immediately
            - 5xx errors (server fault): Retry with exponential backoff
            - Timeout/Connection errors: Retry with exponential backoff
            - Backoff formula: 2^attempt + jitter (0-1 second)
        """
        for attempt in range(self.retry_attempts):
            try:
                self.logger.debug(f"Sending {request_type} (attempt {attempt + 1}/{self.retry_attempts})")

                response = requests.post(
                    endpoint,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout,
                    verify=True  # Validate SSL certificates
                )

                # Success
                if response.status_code == 200:
                    self.logger.info(f"Successfully sent {request_type} to Firebase")
                    return True

                # Client error (4xx) - don't retry
                elif 400 <= response.status_code < 500:
                    self.logger.error(f"Client error {response.status_code} for {request_type}: {response.text}")
                    return False

                # Server error (5xx) - retry
                else:
                    self.logger.warning(f"Server error {response.status_code} for {request_type}: {response.text}")

            except requests.exceptions.Timeout:
                self.logger.warning(f"Request timeout for {request_type} (attempt {attempt + 1})")

            except requests.exceptions.ConnectionError as e:
                self.logger.warning(f"Connection error for {request_type}: {e}")

            except requests.exceptions.RequestException as e:
                self.logger.error(f"Request error for {request_type}: {e}")

            except Exception as e:
                self.logger.error(f"Unexpected error sending {request_type}: {e}")

            # Exponential backoff with jitter before retry
            if attempt < self.retry_attempts - 1:
                # 2^attempt + random jitter (0-1 second)
                wait_time = (2 ** attempt) + (time.time() % 1)
                self.logger.info(f"Retrying {request_type} in {wait_time:.1f} seconds...")
                time.sleep(wait_time)

        # All retries exhausted
        self.logger.error(f"Failed to send {request_type} after {self.retry_attempts} attempts")
        return False

    def test_connection(self):
        """Test connectivity to Firebase endpoints.

        Returns:
            dict: Test results for each configured endpoint
        """
        results = {}

        for endpoint_name, endpoint_url in self.endpoints.items():
            if not endpoint_url:
                results[endpoint_name] = {'status': 'not_configured'}
                continue

            try:
                # Simple HEAD request to test connectivity
                response = requests.head(endpoint_url, timeout=self.timeout, verify=True)
                results[endpoint_name] = {
                    'status': 'reachable',
                    'status_code': response.status_code
                }
                self.logger.info(f"Endpoint '{endpoint_name}' is reachable (status {response.status_code})")

            except requests.exceptions.Timeout:
                results[endpoint_name] = {'status': 'timeout'}
                self.logger.warning(f"Endpoint '{endpoint_name}' timed out")

            except requests.exceptions.ConnectionError:
                results[endpoint_name] = {'status': 'unreachable'}
                self.logger.warning(f"Endpoint '{endpoint_name}' is unreachable")

            except Exception as e:
                results[endpoint_name] = {'status': 'error', 'message': str(e)}
                self.logger.error(f"Error testing endpoint '{endpoint_name}': {e}")

        return results

    def get_config(self):
        """Get current transport configuration.

        Returns:
            dict: Current configuration settings
        """
        return {
            'camera_id': self.camera_id,
            'site_id': self.site_id,
            'endpoints': self.endpoints,
            'report_interval': self.report_interval,
            'retry_attempts': self.retry_attempts,
            'timeout': self.timeout
        }
