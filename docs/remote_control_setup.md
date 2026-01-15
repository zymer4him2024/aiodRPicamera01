# Remote Control Installation Guide

This guide will help you enable remote start/stop control for your RPi Object Detection system.

## Manual Installation (On the RPi)

### Step 1: Create the Command Listener

SSH into your RPi and create the command listener file:

```bash
cd ~/camera-system
cat << 'EOF' > utils/command_listener.py
import threading
import time
import requests
from google.cloud import firestore
from utils.logger import get_logger

class CommandListener:
    def __init__(self, serial_number, local_api_port=5000):
        self.logger = get_logger(self.__class__.__name__)
        self.serial = serial_number
        self.local_api_port = local_api_port
        self.db = firestore.Client()
        self.running = False
        self.thread = None
        
    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()
        self.logger.info("CommandListener started")
    
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
    
    def _listen_loop(self):
        while self.running:
            try:
                commands_ref = self.db.collection('commands')
                query = commands_ref.where('serial', '==', self.serial)\
                                   .where('status', '==', 'pending')\
                                   .order_by('created_at')\
                                   .limit(1)
                
                docs = query.stream()
                
                for doc in docs:
                    command_data = doc.to_dict()
                    action = command_data.get('action')
                    
                    self.logger.info(f"Executing command: {action}")
                    success = self._execute_command(action)
                    
                    doc.reference.update({
                        'status': 'executed' if success else 'failed',
                        'executed_at': firestore.SERVER_TIMESTAMP,
                        'error': None if success else 'Execution failed'
                    })
                    
            except Exception as e:
                self.logger.error(f"Error in command listener: {e}")
            
            time.sleep(3)
    
    def _execute_command(self, action):
        try:
            if action == 'start':
                url = f"http://localhost:{self.local_api_port}/start"
            elif action == 'stop':
                url = f"http://localhost:{self.local_api_port}/stop"
            else:
                return False
            
            response = requests.post(url, timeout=5)
            return response.status_code == 200
            
        except Exception as e:
            self.logger.error(f"Failed to execute {action}: {e}")
            return False
EOF
```

### Step 2: Update main.py

Add the command listener startup code to `main.py`:

```bash
nano ~/camera-system/main.py
```

Add these lines after `time.sleep(1)` and before the orchestrator initialization:

```python
    # 2.5. Start Command Listener for remote control
    from utils.command_listener import CommandListener
    from utils.binding_manager import BindingManager
    
    binding = BindingManager()
    if binding.is_bound():
        cmd_listener = CommandListener(binding.serial_number)
        cmd_listener.start()
        logger.info("Remote command listener started")
    else:
        logger.warning("Device not bound - remote control disabled")
```

### Step 3: Restart the Service

```bash
sudo systemctl restart aiod-counter
```

### Step 4: Verify Installation

Check the logs to confirm the command listener started:

```bash
journalctl -u aiod-counter -f | grep -i "command"
```

You should see: `Remote command listener started`

## How It Works

1. **Dashboard** → User clicks Play/Stop button
2. **Firestore** → Command is written to `commands` collection
3. **RPi** → Command listener polls Firestore every 3 seconds
4. **Local API** → Command listener calls `/start` or `/stop` endpoint
5. **Status** → Green indicator appears when data is received (< 30 sec)

## Troubleshooting

### Command listener not starting
- Check if device is bound: `cat ~/camera-system/config/binding.json`
- Ensure Firestore credentials are configured
- Check logs: `journalctl -u aiod-counter -n 50`

### Commands not executing
- Verify internet connection on RPi
- Check Firestore indexes are deployed
- Test local API: `curl -X POST http://localhost:5000/start`

### Status indicator always red
- Check if orchestrator is running: `systemctl status aiod-counter`
- Verify data is being sent to Firebase
- Look for network issues in logs
