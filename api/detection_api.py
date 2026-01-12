from flask import Flask, request, jsonify, send_from_directory, Response, make_response

import time
from agents.orchestrator import Orchestrator
from utils.logger import get_logger

app = Flask(__name__)
logger = get_logger("DetectionAPI")

# Global orchestrator instance
orchestrator = None

def get_orchestrator():
    global orchestrator
    if orchestrator is None:
        try:
            orchestrator = Orchestrator()
        except Exception as e:
            logger.error(f"Failed to initialize orchestrator: {e}")
            return None
    return orchestrator

# Add dashboard routes
@app.route('/')
@app.route('/dashboard')
def dashboard():
    response = make_response(send_from_directory('static', 'index.html'))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return response

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.before_request
def log_request_info():
    logger.info(f"Request: {request.method} {request.url}")

@app.route('/health', methods=['GET'])
def health_check():
    orch = get_orchestrator()
    status = "healthy" if orch else "degraded"
    return jsonify({
        "status": status,
        "timestamp": time.time(),
        "camera_id": orch.transport.config.get("camera_id") if orch else "unknown"
    }), 200

@app.route('/api/detection/start', methods=['POST'])
def start_detection():
    orch = get_orchestrator()
    if not orch:
        return jsonify({"error": "Orchestrator not initialized"}), 500

    try:
        # Check for optional config overrides - safely handle missing body
        data = request.get_json(silent=True) or {}
        if "report_interval" in data:
            orch.report_interval = float(data["report_interval"])
        
        # We could also pass backend_url override to transport agent if needed
        # but for now we stick to requirements.
        
        orch.start_detection()
        return jsonify({"status": "success", "message": "Detection started"}), 200
    except Exception as e:
        logger.error(f"Error starting detection: {e}")
        return jsonify({"status": "failure", "error": str(e)}), 500

@app.route('/api/detection/stop', methods=['POST'])
def stop_detection():
    orch = get_orchestrator()
    if not orch:
         return jsonify({"error": "Orchestrator not initialized"}), 500
    
    try:
        orch.stop_detection()
        return jsonify({"status": "success", "message": "Detection stopped"}), 200
    except Exception as e:
        logger.error(f"Error stopping detection: {e}")
        return jsonify({"status": "failure", "error": str(e)}), 500

@app.route('/api/detection/status', methods=['GET'])
def get_status():
    orch = get_orchestrator()
    if not orch:
         return jsonify({"status": "error", "message": "Orchestrator not initialized"}), 500

    uptime = 0
    if orch.running and hasattr(orch, 'start_time'):
        uptime = time.time() - orch.start_time

    logger.info(f"API_STATUS: Active={orch.running}, LatestCounts={orch.latest_counts}")
    return jsonify({
        "active": orch.running,
        "camera_id": orch.transport.config.get("camera_id"),
        "uptime": f"{uptime:.2f}s" if uptime > 0 else "N/A",
        "last_count_sent": getattr(orch, 'last_report_time_str', "N/A"),
        "latest_counts": getattr(orch, 'latest_counts', {})
    }), 200

def generate_frames():
    orch = get_orchestrator()
    while True:
        if orch and orch.last_annotated_frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + orch.last_annotated_frame + b'\r\n')
        time.sleep(0.1) # Limit streaming to ~10 FPS to save bandwidth

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    # In production, use a WSGI server like gunicorn
    app.run(host='0.0.0.0', port=5000)
