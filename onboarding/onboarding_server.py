"""
RPi Onboarding Server - Local web interface for device activation

This server runs on the RPi and provides:
1. QR code generation for device discovery
2. Mobile-friendly onboarding web page
3. Site selection and device activation
4. Backend handshake coordination

Usage:
    python3 onboarding_server.py
    
Then scan the QR code displayed or navigate to http://<rpi-ip>:8080
"""

from flask import Flask, render_template_string, jsonify, request, send_file
import socket
import json
import os
import io
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.binding_manager import BindingManager
from agents.handshake_agent import HandshakeAgent
from utils.network_manager import NetworkManager
import threading
import time

app = Flask(__name__)
binding_manager = BindingManager()
handshake_agent = HandshakeAgent(binding_manager=binding_manager)
network_manager = NetworkManager()

# Configuration
ONBOARDING_PORT = 8080
BACKEND_URL = "https://us-central1-aiodcounter06.cloudfunctions.net/api"

def get_local_ip():
    """Get the device's local IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

# Modern, Apple-inspired onboarding page
ONBOARDING_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Device Activation</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        :root {
            --bg-primary: #0a0a0f;
            --bg-secondary: #12121a;
            --bg-card: #1a1a24;
            --accent: #00d4ff;
            --accent-glow: rgba(0, 212, 255, 0.3);
            --success: #00ff88;
            --warning: #ffaa00;
            --danger: #ff4466;
            --text-primary: #ffffff;
            --text-secondary: rgba(255, 255, 255, 0.6);
            --border: rgba(255, 255, 255, 0.1);
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 2rem 1rem;
        }
        
        .container {
            max-width: 480px;
            width: 100%;
        }
        
        .header {
            text-align: center;
            margin-bottom: 2rem;
        }
        
        .logo {
            width: 80px;
            height: 80px;
            background: linear-gradient(135deg, var(--accent), #0088ff);
            border-radius: 20px;
            margin: 0 auto 1.5rem;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 10px 40px var(--accent-glow);
        }
        
        .logo svg {
            width: 48px;
            height: 48px;
            fill: white;
        }
        
        h1 {
            font-size: 1.75rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            background: linear-gradient(135deg, #fff, var(--accent));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .subtitle {
            color: var(--text-secondary);
            font-size: 0.95rem;
        }
        
        .card {
            background: var(--bg-card);
            border-radius: 16px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            border: 1px solid var(--border);
        }
        
        .card-header {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 1rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border);
        }
        
        .card-title {
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--text-secondary);
        }
        
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            padding: 0.25rem 0.75rem;
            border-radius: 100px;
            font-size: 0.7rem;
            font-weight: 600;
            text-transform: uppercase;
        }
        
        .status-badge.unbound {
            background: rgba(255, 170, 0, 0.15);
            color: var(--warning);
        }
        
        .status-badge.bound {
            background: rgba(0, 255, 136, 0.15);
            color: var(--success);
        }
        
        .info-row {
            display: flex;
            justify-content: space-between;
            padding: 0.75rem 0;
            border-bottom: 1px solid var(--border);
        }
        
        .info-row:last-child { border-bottom: none; }
        
        .info-label {
            color: var(--text-secondary);
            font-size: 0.85rem;
        }
        
        .info-value {
            font-family: 'SF Mono', 'Fira Code', monospace;
            font-size: 0.85rem;
            color: var(--accent);
        }
        
        .form-group {
            margin-bottom: 1.25rem;
        }
        
        label {
            display: block;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-secondary);
            margin-bottom: 0.5rem;
        }
        
        select, input {
            width: 100%;
            padding: 1rem;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 12px;
            color: var(--text-primary);
            font-size: 1rem;
            transition: all 0.2s ease;
        }
        
        select:focus, input:focus {
            outline: none;
            border-color: var(--accent);
            box-shadow: 0 0 0 3px var(--accent-glow);
        }
        
        .btn {
            width: 100%;
            padding: 1rem;
            border: none;
            border-radius: 12px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, var(--accent), #0088ff);
            color: white;
            box-shadow: 0 4px 20px var(--accent-glow);
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 30px var(--accent-glow);
        }
        
        .btn-primary:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
        
        .btn-danger {
            background: rgba(255, 68, 102, 0.15);
            color: var(--danger);
            border: 1px solid rgba(255, 68, 102, 0.3);
        }
        
        .message {
            padding: 1rem;
            border-radius: 12px;
            margin-bottom: 1rem;
            display: none;
        }
        
        .message.success {
            background: rgba(0, 255, 136, 0.1);
            border: 1px solid rgba(0, 255, 136, 0.3);
            color: var(--success);
            display: block;
        }
        
        .message.error {
            background: rgba(255, 68, 102, 0.1);
            border: 1px solid rgba(255, 68, 102, 0.3);
            color: var(--danger);
            display: block;
        }
        
        .spinner {
            width: 20px;
            height: 20px;
            border: 2px solid rgba(255,255,255,0.3);
            border-top-color: white;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .footer {
            text-align: center;
            margin-top: 2rem;
            color: var(--text-secondary);
            font-size: 0.75rem;
        }
        
        /* Already bound state */
        .bound-card {
            text-align: center;
            padding: 2rem;
        }
        
        .bound-icon {
            width: 64px;
            height: 64px;
            background: rgba(0, 255, 136, 0.15);
            border-radius: 50%;
            margin: 0 auto 1rem;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .bound-icon svg {
            width: 32px;
            height: 32px;
            stroke: var(--success);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
                    <circle cx="12" cy="13" r="4"/>
                </svg>
            </div>
            <h1>Device Activation</h1>
            <p class="subtitle">AI Object Detection Camera</p>
        </div>
        
        <!-- Device Info Card -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">Device Information</span>
                <span class="status-badge {{ 'bound' if is_bound else 'unbound' }}" id="statusBadge">
                    {{ 'Active' if is_bound else 'Unbound' }}
                </span>
            </div>
            <div class="info-row">
                <span class="info-label">Serial Number</span>
                <span class="info-value">{{ serial }}</span>
            </div>
            <div class="info-row">
                <span class="info-label">IP Address</span>
                <span class="info-value">{{ ip_address }}</span>
            </div>
            {% if is_bound %}
            <div class="info-row">
                <span class="info-label">Camera ID</span>
                <span class="info-value">{{ camera_id }}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Site</span>
                <span class="info-value">{{ site_name }}</span>
            </div>
            {% endif %}
        </div>
        
        <!-- Message Area -->
        <div class="message" id="message"></div>
        
        {% if is_bound %}
        <!-- Already Bound -->
        <div class="card bound-card">
            <div class="bound-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke-width="2">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                    <polyline points="22 4 12 14.01 9 11.01"/>
                </svg>
            </div>
            <h2 style="margin-bottom: 0.5rem;">Device Active</h2>
            <p style="color: var(--text-secondary); margin-bottom: 1.5rem;">
                This device is bound and sending data to the backend.
            </p>
            <button class="btn btn-danger" onclick="resetDevice()">
                Reset Device
            </button>
        </div>
        {% else %}
        <!-- Activation Form -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">Activate Device</span>
            </div>
            
            <form id="activationForm" onsubmit="activateDevice(event)">
                <div class="form-group">
                    <label for="siteSelect">Select Site</label>
                    <select id="siteSelect" required>
                        <option value="">Loading sites...</option>
                    </select>
                </div>

                <div class="form-group">
                    <label style="display: flex; align-items: center; gap: 0.5rem; cursor: pointer;">
                        <input type="checkbox" id="wifiToggle" checked onchange="toggleWifiFields()" style="width: auto; margin: 0;">
                        Configure WiFi Connection
                    </label>
                </div>

                <div id="wifiFields">
                    <div class="form-group">
                        <label for="wifiSsid">WiFi Network (SSID)</label>
                        <select id="wifiSsid">
                            <option value="">Scanning networks...</option>
                        </select>
                        <input type="text" id="wifiSsidManual" placeholder="Enter SSID manually" style="display: none; margin-top: 0.5rem;">
                        <div style="text-align: right; margin-top: 0.25rem;">
                            <a href="#" onclick="toggleManualSsid(event)" style="font-size: 0.75rem; color: var(--accent); text-decoration: none;">Toggle Manual Entry</a>
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label for="wifiPassword">WiFi Password</label>
                        <input type="password" id="wifiPassword" placeholder="Enter WiFi Password">
                    </div>
                </div>
                
                <button type="submit" class="btn btn-primary" id="activateBtn">
                    <span id="btnText">Save & Connect</span>
                    <div class="spinner" id="btnSpinner" style="display: none;"></div>
                </button>
            </form>
        </div>
        {% endif %}

        <!-- Success/Switching Network Card (Hidden by default) -->
        <div class="card" id="successCard" style="display: none; text-align: center; padding: 2.5rem 1.5rem;">
            <div style="width: 64px; height: 64px; background: rgba(0, 255, 136, 0.15); border-radius: 50%; margin: 0 auto 1.5rem; display: flex; align-items: center; justifyContent: center;">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width: 32px; height: 32px; stroke: var(--success);">
                     <path d="M5 12.55a11 11 0 0 1 14.08 0"></path>
                     <path d="M1.42 9a16 16 0 0 1 21.16 0"></path>
                     <path d="M8.53 16.11a6 6 0 0 1 6.95 0"></path>
                     <line x1="12" y1="20" x2="12.01" y2="20"></line>
                </svg>
            </div>
            <h2 style="margin-bottom: 1rem; color: white;">Connecting...</h2>
            <p style="color: var(--text-secondary); margin-bottom: 2rem; line-height: 1.6;" id="successMessage">
                Device is switching to WiFi.
            </p>
            
            <div style="background: rgba(255, 170, 0, 0.1); border: 1px solid rgba(255, 170, 0, 0.3); padding: 1rem; border-radius: 12px; text-align: left; margin-bottom: 2rem;">
                <div style="font-size: 0.7rem; text-transform: uppercase; color: var(--warning); font-weight: 700; margin-bottom: 0.5rem;">Action Required</div>
                <div style="font-size: 0.9rem; color: #ffdca8;">
                    1. Disconnect from "AIOD-Installer" WiFi.<br>
                    2. Connect your phone to <strong><span id="targetSsid">target network</span></strong>.<br>
                    3. Check the Dashboard for device status.
                </div>
            </div>
            
            <button class="btn" style="background: var(--bg-secondary); color: var(--text-secondary);" onclick="window.location.reload()">
                Reload Page
            </button>
        </div>
        
        <div class="footer">
            <p>AIOD Camera System v1.1</p>
            <p style="margin-top: 0.25rem;">© 2026 Global Innovation</p>
        </div>
    </div>
    
    <script>
        const BACKEND_URL = '{{ backend_url }}';
        
        // Load available sites and wifi on page load
        document.addEventListener('DOMContentLoaded', function() {
            {% if not is_bound %}
            loadSites();
            scanWifi();
            {% endif %}
        });
        
        function toggleWifiFields() {
            const enabled = document.getElementById('wifiToggle').checked;
            document.getElementById('wifiFields').style.display = enabled ? 'block' : 'none';
            document.getElementById('btnText').textContent = enabled ? 'Save & Connect' : 'Activate Device';
        }

        function toggleManualSsid(e) {
            e.preventDefault();
            const select = document.getElementById('wifiSsid');
            const input = document.getElementById('wifiSsidManual');
            if (input.style.display === 'none') {
                input.style.display = 'block';
                select.style.display = 'none';
                input.value = select.value;
            } else {
                input.style.display = 'none';
                select.style.display = 'block';
            }
        }

        async function scanWifi() {
            const select = document.getElementById('wifiSsid');
            try {
                const response = await fetch('/api/scan-wifi');
                const result = await response.json();
                
                if (result.success && result.networks) {
                    select.innerHTML = '<option value="">Select Network...</option>';
                    if (result.networks.length === 0) {
                        select.innerHTML += '<option disabled>No networks found</option>';
                    }
                    result.networks.forEach(ssid => {
                        const option = document.createElement('option');
                        option.value = ssid;
                        option.textContent = ssid;
                        select.appendChild(option);
                    });
                } else {
                    select.innerHTML = '<option value="">Scan failed</option>';
                }
            } catch (error) {
                console.error('WiFi scan error:', error);
                select.innerHTML = '<option value="">Scan failed</option>';
            }
        }
        
        async function loadSites() {
            const select = document.getElementById('siteSelect');
            try {
                // Fetch sites from backend (public endpoint needed)
                const response = await fetch(`${BACKEND_URL}/public/sites`);
                if (!response.ok) throw new Error('Failed to load sites');
                
                const sites = await response.json();
                select.innerHTML = '<option value="">Select a site...</option>';
                
                // Get URL Params for auto-selection
                const urlParams = new URLSearchParams(window.location.search);
                const preSelectId = urlParams.get('site_id');
                const preSelectOrg = urlParams.get('org_id');
                let foundPreSelection = false;

                sites.forEach(site => {
                    const option = document.createElement('option');
                    option.value = JSON.stringify({ 
                        site_id: site.id, 
                        org_id: site.org_id,
                        site_name: site.name 
                    });
                    
                    if (preSelectId && site.id === preSelectId) {
                        option.selected = true;
                        foundPreSelection = true;
                    }
                    
                    option.textContent = `${site.name} (${site.org_name || site.org_id})`;
                    select.appendChild(option);
                });
                
                if (foundPreSelection) {
                    showMessage('Site pre-selected from QR Code', 'success');
                }
                
            } catch (error) {
                console.error('Error loading sites:', error);
                // Fallback: use hardcoded test site
                select.innerHTML = `
                    <option value="">Select a site...</option>
                    <option value='{"site_id":"global-innovation-anaheim-001","org_id":"global-innovation","site_name":"Anaheim 001"}'>
                        Anaheim 001 (Global Innovation)
                    </option>
                `;
            }
        }
        
        async function activateDevice(event) {
            event.preventDefault();
            
            const btn = document.getElementById('activateBtn');
            const btnText = document.getElementById('btnText');
            const spinner = document.getElementById('btnSpinner');
            const message = document.getElementById('message');
            const select = document.getElementById('siteSelect');
            
            if (!select.value) {
                showMessage('Please select a site', 'error');
                return;
            }
            
            const siteData = JSON.parse(select.value);
            
            // Add WiFi data if enabled
            if (document.getElementById('wifiToggle').checked) {
                const ssidInput = document.getElementById('wifiSsidManual');
                const ssidSelect = document.getElementById('wifiSsid');
                const ssid = ssidInput.style.display !== 'none' ? ssidInput.value : ssidSelect.value;
                const password = document.getElementById('wifiPassword').value;

                if (!ssid) {
                    showMessage('Please select or enter a WiFi network', 'error');
                    return;
                }
                
                siteData.wifi_ssid = ssid;
                siteData.wifi_password = password;
            }
            
            // Show loading state
            btn.disabled = true;
            btnText.textContent = 'Activating...';
            spinner.style.display = 'block';
            message.style.display = 'none';
            
            try {
                // Call local RPi endpoint to trigger handshake
                const response = await fetch('/api/activate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(siteData)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    if (result.action === 'switch_network') {
                         // HIDE FORM -> SHOW SUCCESS CARD
                         const formCard = document.querySelector('form').closest('.card');
                         if (formCard) formCard.style.display = 'none';
                         
                         const successCard = document.getElementById('successCard');
                         const targetSsidSpan = document.getElementById('targetSsid');
                         if (successCard && targetSsidSpan) {
                             targetSsidSpan.textContent = result.new_ssid || siteData.wifi_ssid || 'Target Network';
                             successCard.style.display = 'block';
                             
                             // Scroll to top
                             window.scrollTo({ top: 0, behavior: 'smooth' });
                         }
                    } else {
                        showMessage('Device activated successfully! Reloading...', 'success');
                        setTimeout(() => window.location.reload(), 2000);
                    }
                } else {
                    throw new Error(result.error || 'Activation failed');
                }
            } catch (error) {
                showMessage(error.message, 'error');
                btn.disabled = false;
                btnText.textContent = 'Save & Connect';
                spinner.style.display = 'none';
            }
        }
        
        async function resetDevice() {
            if (!confirm('Are you sure you want to reset this device? It will need to be re-activated.')) {
                return;
            }
            
            try {
                const response = await fetch('/api/reset', { method: 'POST' });
                const result = await response.json();
                
                if (result.success) {
                    showMessage('Device reset. Reloading...', 'success');
                    setTimeout(() => window.location.reload(), 1500);
                } else {
                    throw new Error(result.error);
                }
            } catch (error) {
                showMessage('Reset failed: ' + error.message, 'error');
            }
        }
        
        function showMessage(text, type) {
            const message = document.getElementById('message');
            message.textContent = text;
            message.className = 'message ' + type;
            message.style.display = 'block';
        }
    </script>
</body>
</html>
'''


@app.route('/')
@app.route('/onboard')
def onboard_page():
    """Serve the onboarding page."""
    info = binding_manager.get_info()
    
    return render_template_string(
        ONBOARDING_HTML,
        serial=info['serial'],
        ip_address=get_local_ip(),
        is_bound=info['bound'],
        camera_id=info.get('camera_id', 'N/A'),
        site_name=info.get('site_id', 'N/A'),
        backend_url=BACKEND_URL
    )


@app.route('/qr')
def generate_qr():
    """Generate QR code image for device discovery."""
    try:
        import qrcode
        from io import BytesIO
        
        local_ip = get_local_ip()
        onboard_url = f"http://{local_ip}:{ONBOARDING_PORT}/onboard"
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(onboard_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        return send_file(buffer, mimetype='image/png')
    except ImportError:
        return jsonify({
            "error": "qrcode module not installed",
            "url": f"http://{get_local_ip()}:{ONBOARDING_PORT}/onboard"
        }), 500


@app.route('/api/scan-wifi')
def scan_wifi():
    """Scan for available WiFi networks."""
    try:
        networks = network_manager.scan_networks()
        return jsonify({"success": True, "networks": networks})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/status')
def status():
    """Return current device status."""
    info = binding_manager.get_info()
    info['ip_address'] = get_local_ip()
    return jsonify(info)


@app.route('/api/activate', methods=['POST'])
def activate():
    """Activate the device with selected site and optional WiFi."""
    try:
        data = request.json
        site_id = data.get('site_id')
        org_id = data.get('org_id')
        wifi_ssid = data.get('wifi_ssid')
        wifi_password = data.get('wifi_password')
        
        if not site_id or not org_id:
            return jsonify({"success": False, "error": "Missing site_id or org_id"}), 400
        
        # Prepare handshake logic
        def run_handshake_flow():
            import requests # re-import for thread safety if needed
            import hashlib
            import time
            
            # 1. Network Switch (if WiFi provided)
            if wifi_ssid:
                print(f"Switching to WiFi: {wifi_ssid}")
                if network_manager.connect_to_wifi(wifi_ssid, wifi_password):
                    # verify internet
                    retries = 10
                    while retries > 0:
                        if network_manager.check_internet():
                            print("Internet verified.")
                            break
                        time.sleep(2)
                        retries -= 1
                    
                    if retries == 0:
                        print("Failed to verify internet. Reverting to Hotspot.")
                        # Revert!
                        # Assuming we know hotspot details? 
                        # Hardcoding or reading from config would be better.
                        network_manager.create_hotspot("AIOD-Installer", "aiod1234")
                        return False
                else:
                    print("Failed to connect to WiFi. Reverting...")
                    network_manager.create_hotspot("AIOD-Installer", "aiod1234")
                    return False
            
            # 2. Token Generation & Handshake (now we have internet)
            try:
                # Create a deterministic token based on serial + timestamp
                serial = binding_manager.serial_number
                token_base = f"{serial}_{site_id}_{int(time.time())}"
                token = hashlib.sha256(token_base.encode()).hexdigest()
                
                # First, seed the token in the backend
                seed_response = requests.post(
                    f"{BACKEND_URL}/dev/seed-token",
                    json={"token": token, "site_id": site_id, "org_id": org_id},
                    timeout=30
                )
                
                if seed_response.status_code != 201:
                    print(f"Seed failed: {seed_response.text}")
                    # If we switched network, maybe we should revert? 
                    # But maybe partial success is okay? No, user needs to retry.
                    if wifi_ssid: network_manager.create_hotspot("AIOD-Installer", "aiod1234")
                    return False
                
                # Now perform the handshake with this token
                qr_payload = {
                    "backend_url": BACKEND_URL,
                    "token": token,
                    "site_id": site_id,
                    "org_id": org_id
                }
                
                result = handshake_agent.perform_handshake(qr_payload)
                if result:
                    print("Handshake SUCCESS!")
                    return True
                else:
                    print("Handshake FAILED.")
                    if wifi_ssid: network_manager.create_hotspot("AIOD-Installer", "aiod1234")
                    return False
                    
            except Exception as e:
                print(f"Handshake error: {e}")
                if wifi_ssid: network_manager.create_hotspot("AIOD-Installer", "aiod1234")
                return False

        # If WiFi is provided, run async
        if wifi_ssid:
            thread = threading.Thread(target=run_handshake_flow)
            thread.start()
            return jsonify({
                "success": True,
                "message": "Connecting to WiFi Network... You may lose connection.",
                "action": "switch_network",
                "new_ssid": wifi_ssid
            })
        else:
            # Synchronous (Ethernet or existing connection)
            # Just call the inner logic synchronously (adapted slightly)
            # Actually, just simpler to reuse logic? But `run_handshake_flow` does revert logic which we don't need for ethernet.
            
            # Let's keep existing synchronous logic for non-WiFi case for simplicity/robustness
            import requests, hashlib, time
            serial = binding_manager.serial_number
            token_base = f"{serial}_{site_id}_{int(time.time())}"
            token = hashlib.sha256(token_base.encode()).hexdigest()
            
            seed_response = requests.post(
                f"{BACKEND_URL}/dev/seed-token",
                json={"token": token, "site_id": site_id, "org_id": org_id},
                timeout=30
            )
            
            if seed_response.status_code != 201:
                 return jsonify({"success": False, "error": f"Seed failed: {seed_response.text}"}), 500

            qr_payload = {
                    "backend_url": BACKEND_URL,
                    "token": token,
                    "site_id": site_id,
                    "org_id": org_id
            }
            if handshake_agent.perform_handshake(qr_payload):
                return jsonify({"success": True, "message": "Device activated successfully", "binding": binding_manager.get_info()})
            else:
                return jsonify({"success": False, "error": "Handshake failed"}), 500

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/reset', methods=['POST'])
def reset():
    """Reset the device to unbound state."""
    try:
        handshake_agent.reset()
        return jsonify({"success": True, "message": "Device reset"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def display_qr_on_screen():
    """Display QR code on RPi screen (requires display)."""
    try:
        import qrcode
        
        local_ip = get_local_ip()
        onboard_url = f"http://{local_ip}:{ONBOARDING_PORT}/onboard"
        
        print("\n" + "="*50)
        print("  DEVICE ONBOARDING")
        print("="*50)
        print(f"\n  Scan QR code or navigate to:")
        print(f"  {onboard_url}")
        print("\n  QR Code (ASCII):")
        
        # Generate ASCII QR code for terminal
        qr = qrcode.QRCode()
        qr.add_data(onboard_url)
        qr.print_ascii(invert=True)
        
        print("\n" + "="*50 + "\n")
    except ImportError:
        local_ip = get_local_ip()
        print(f"\nOnboarding URL: http://{local_ip}:{ONBOARDING_PORT}/onboard")
        print("(Install qrcode module for QR display: pip install qrcode)")


if __name__ == '__main__':
    display_qr_on_screen()
    print(f"Starting onboarding server on port {ONBOARDING_PORT}...")
    app.run(host='0.0.0.0', port=ONBOARDING_PORT, debug=False)
