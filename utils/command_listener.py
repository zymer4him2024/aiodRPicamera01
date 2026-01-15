import threading
import time
import requests
import io
from google.cloud import firestore
from google.cloud import storage
from utils.logger import get_logger
from utils.binding_manager import BindingManager

class CommandListener:
    def __init__(self, serial_number, local_api_port=5000):
        self.logger = get_logger(self.__class__.__name__)
        self.serial = serial_number
        self.local_api_port = local_api_port
        self.db = firestore.Client()
        self.storage_client = storage.Client()
        self.running = False
        self.thread = None
        
        # Get camera metadata for snapshot uploads
        self.binding = BindingManager()
        
    def start(self):
        if self.running: return
        self.running = True
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()
        self.logger.info("Remote Command Listener started")
    
    def stop(self):
        self.running = False
        if self.thread: self.thread.join(timeout=5)
    
    def _listen_loop(self):
        while self.running:
            try:
                # Poll for pending commands
                docs = self.db.collection('commands')\
                               .where('serial', '==', self.serial)\
                               .where('status', '==', 'pending')\
                               .order_by('created_at')\
                               .limit(1).stream()
                
                for doc in docs:
                    command_data = doc.to_dict()
                    action = command_data.get('action')
                    self.logger.info(f"Executing remote command: {action}")
                    
                    if action == 'snapshot':
                        success, result = self._handle_snapshot(command_data)
                    else:
                        success, result = self._handle_control_command(action)
                    
                    # Update command status
                    update_data = {
                        'status': 'executed' if success else 'failed',
                        'executed_at': firestore.SERVER_TIMESTAMP
                    }
                    if result:
                        update_data['result'] = result
                    
                    doc.reference.update(update_data)
                    
            except Exception as e:
                self.logger.error(f"Command Error: {e}")
            time.sleep(3)
    
    def _handle_control_command(self, action):
        """Handle start/stop commands"""
        try:
            url = f"http://localhost:{self.local_api_port}/{action}"
            res = requests.post(url, timeout=5)
            return res.status_code == 200, None
        except Exception as e:
            self.logger.error(f"Control command failed: {e}")
            return False, str(e)
    
    def _handle_snapshot(self, command_data):
        """Capture snapshot and upload to Firebase Storage"""
        try:
            # Get snapshot from local API
            url = f"http://localhost:{self.local_api_port}/snapshot"
            response = requests.post(url, timeout=10)
            
            if response.status_code != 200:
                return False, "Failed to capture snapshot"
            
            # Get metadata
            org_id = self.binding.org_id
            camera_id = self.binding.camera_id
            timestamp = int(time.time() * 1000)  # milliseconds
            
            # Upload to Firebase Storage
            bucket = self.storage_client.bucket()
            blob_path = f"snapshots/{org_id}/{camera_id}/{timestamp}.jpg"
            blob = bucket.blob(blob_path)
            
            blob.upload_from_string(
                response.content,
                content_type='image/jpeg'
            )
            
            # Create snapshot metadata in Firestore
            snapshot_ref = self.db.collection('snapshots').document()
            snapshot_ref.set({
                'camera_id': camera_id,
                'org_id': org_id,
                'site_id': self.binding.site_id,
                'serial': self.serial,
                'storage_path': blob_path,
                'timestamp': firestore.SERVER_TIMESTAMP,
                'requested_by': command_data.get('requested_by', 'unknown')
            })
            
            self.logger.info(f"Snapshot uploaded: {blob_path}")
            return True, {'storage_path': blob_path, 'snapshot_id': snapshot_ref.id}
            
        except Exception as e:
            self.logger.error(f"Snapshot failed: {e}")
            return False, str(e)

