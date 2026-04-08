import subprocess
from utils.logger import get_logger
import time

class NetworkManager:
    """
    Wrapper for nmcli to manage network connections on RPi.
    Handles Hotspot (AP) creation and Client (WiFi) connection.
    """
    
    def __init__(self, interface="wlan0"):
        self.logger = get_logger(self.__class__.__name__)
        self.interface = interface

    def _run_command(self, command):
        """Runs a shell command and returns output."""
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                check=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            return True, result.stdout.strip()
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Command failed: {command}\nError: {e.stderr}")
            return False, e.stderr.strip()

    def scan_networks(self):
        """Scans for available WiFi networks."""
        self.logger.info("Scanning for networks...")
        # -t: terse (machine readable), -f: fields
        # Rescan first
        self._run_command(f"nmcli device wifi rescan ifname {self.interface}")
        time.sleep(2) # Wait for scan results
        
        success, output = self._run_command(f"nmcli -t -f SSID,SIGNAL,SECURITY device wifi list ifname {self.interface}")
        if not success:
            return []
            
        networks = []
        seen_ssids = set()
        
        for line in output.split('\n'):
            if not line: continue
            parts = line.split(':') # Careful: SSID might contain colons, usually escaped? nmcli -t escapes them with \
            # Simple parsing for now, assuming standard SSIDs
            if len(parts) >= 1:
                ssid = parts[0]
                if ssid and ssid not in seen_ssids:
                    networks.append(ssid)
                    seen_ssids.add(ssid)
        
        return sorted(networks)

    def connect_to_wifi(self, ssid, password):
        """Connects to a WiFi network (Client Mode)."""
        self.logger.info(f"Connecting to WiFi: {ssid}")
        
        # 1. Delete existing connection with same name if exists
        self._run_command(f"nmcli connection delete '{ssid}'")
        
        # 2. Add new connection
        cmd = f"nmcli device wifi connect '{ssid}' password '{password}' ifname {self.interface}"
        success, output = self._run_command(cmd)
        
        if success:
            self.logger.info(f"Successfully connected to {ssid}")
            return True
        else:
            self.logger.error(f"Failed to connect to {ssid}")
            return False

    def check_internet(self):
        """Checks internet connectivity by pinging Google DNS."""
        success, _ = self._run_command("ping -c 1 -W 2 8.8.8.8")
        return success

    def create_hotspot(self, ssid, password):
        """Creates and activates a Hotspot (AP)."""
        self.logger.info(f"Creating Hotspot: {ssid}")
        
        # 1. Delete existing connections on interface to be safe? 
        # Or specifically the previous client connection? 
        # nmcli handles switching usually, but let's be explicit if needed.
        
        # Delete existing hotspot with same name
        self._run_command(f"nmcli connection delete '{ssid}'")
        
        # 2. Create hotspot connection
        # 802-11-wireless.mode ap 802-11-wireless.band bg ipv4.method shared
        cmd = (
            f"nmcli con add type wifi ifname {self.interface} con-name '{ssid}' "
            f"autoconnect yes ssid '{ssid}' "
            f"802-11-wireless.mode ap 802-11-wireless.band bg "
            f"ipv4.method shared "
            f"wifi-sec.key-mgmt wpa-psk wifi-sec.psk '{password}'"
        )
        
        success, output = self._run_command(cmd)
        if success:
            # 3. Bring it up
            up_success, _ = self._run_command(f"nmcli con up '{ssid}'")
            if up_success:
                self.logger.info(f"Hotspot {ssid} active.")
                return True
        
        self.logger.error("Failed to create hotspot.")
        return False
