#!/usr/bin/env python3
"""
Main entry point for Camera Detection System.

Modes:
  - Standalone: Run orchestrator directly
  - API: Run with Flask API for remote control
  - Daemon: Run as background service

Usage:
  python3 main.py                    # Standalone mode
  python3 main.py --api              # API mode
  python3 main.py --daemon           # Daemon mode
"""

import sys
import os
import argparse
import signal
import time
from pathlib import Path

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.orchestrator import OrchestratorAgent
from utils.logger import setup_logger


# Global orchestrator instance
orchestrator = None
logger = None


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global orchestrator, logger

    if logger:
        logger.info(f"Received signal {signum}, shutting down...")

    print("\nShutting down gracefully...")

    if orchestrator:
        orchestrator.stop()

    sys.exit(0)


def run_standalone(config_dir):
    """Run in standalone mode - orchestrator only."""
    global orchestrator, logger

    logger.info("="*70)
    logger.info(" Camera Detection System - Standalone Mode")
    logger.info("="*70)

    # Initialize orchestrator
    orchestrator = OrchestratorAgent(config_dir=config_dir)

    # Start system
    if not orchestrator.start():
        logger.error("Failed to start system")
        return 1

    logger.info("System started successfully")
    logger.info("Press Ctrl+C to stop")

    try:
        # Keep running
        while True:
            time.sleep(60)

            # Periodic status log
            status = orchestrator.get_status()
            logger.info(f"Status: Uptime={status['uptime_seconds']:.0f}s, "
                       f"Frames={status['metrics']['frames_processed']}, "
                       f"Reports={status['metrics']['reports_sent']}")

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")

    finally:
        orchestrator.stop()
        logger.info("System stopped")

    return 0


def run_api_mode(config_dir, host='0.0.0.0', port=5000):
    """Run with Flask API for remote control."""
    global orchestrator, logger

    try:
        from flask import Flask, jsonify, request
    except ImportError:
        logger.error("Flask not installed. Install with: pip install flask")
        return 1

    logger.info("="*70)
    logger.info(" Camera Detection System - API Mode")
    logger.info("="*70)

    # Create Flask app
    app = Flask(__name__)

    # Initialize orchestrator
    orchestrator = OrchestratorAgent(config_dir=config_dir)

    # API Endpoints

    @app.route('/health', methods=['GET'])
    def health():
        """Health check endpoint."""
        return jsonify({
            'status': 'healthy',
            'timestamp': time.time()
        }), 200

    @app.route('/api/detection/start', methods=['POST'])
    def start_detection():
        """Start detection system."""
        if orchestrator.running:
            return jsonify({'error': 'Already running'}), 400

        if orchestrator.start():
            logger.info("Detection started via API")
            return jsonify({'message': 'Detection started', 'status': 'running'}), 200
        else:
            logger.error("Failed to start detection via API")
            return jsonify({'error': 'Failed to start'}), 500

    @app.route('/api/detection/stop', methods=['POST'])
    def stop_detection():
        """Stop detection system."""
        if not orchestrator.running:
            return jsonify({'error': 'Not running'}), 400

        orchestrator.stop()
        logger.info("Detection stopped via API")
        return jsonify({'message': 'Detection stopped', 'status': 'stopped'}), 200

    @app.route('/api/detection/pause', methods=['POST'])
    def pause_detection():
        """Pause detection (camera keeps running)."""
        if not orchestrator.running:
            return jsonify({'error': 'Not running'}), 400

        orchestrator.pause()
        logger.info("Detection paused via API")
        return jsonify({'message': 'Detection paused', 'status': 'paused'}), 200

    @app.route('/api/detection/resume', methods=['POST'])
    def resume_detection():
        """Resume detection."""
        if not orchestrator.running:
            return jsonify({'error': 'Not running'}), 400

        orchestrator.resume()
        logger.info("Detection resumed via API")
        return jsonify({'message': 'Detection resumed', 'status': 'running'}), 200

    @app.route('/api/detection/status', methods=['GET'])
    def get_status():
        """Get system status."""
        status = orchestrator.get_status()
        return jsonify(status), 200

    @app.route('/api/config/<component>', methods=['GET'])
    def get_config(component):
        """Get configuration for a component."""
        valid_components = ['camera', 'detection', 'counting', 'backend']

        if component not in valid_components:
            return jsonify({'error': f'Invalid component. Valid: {valid_components}'}), 400

        config_file = os.path.join(config_dir, f'{component}_config.json')

        if not os.path.exists(config_file):
            return jsonify({'error': 'Config file not found'}), 404

        import json
        with open(config_file, 'r') as f:
            config = json.load(f)

        return jsonify(config), 200

    # Auto-start if requested
    auto_start = request.args.get('autostart', 'false').lower() == 'true' if '--autostart' in sys.argv else False

    if auto_start:
        logger.info("Auto-starting detection system...")
        orchestrator.start()

    # Start Flask app
    logger.info(f"Starting API server on {host}:{port}")
    logger.info("API Endpoints:")
    logger.info("  GET  /health")
    logger.info("  POST /api/detection/start")
    logger.info("  POST /api/detection/stop")
    logger.info("  POST /api/detection/pause")
    logger.info("  POST /api/detection/resume")
    logger.info("  GET  /api/detection/status")
    logger.info("  GET  /api/config/<component>")

    try:
        app.run(host=host, port=port, threaded=True)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        if orchestrator.running:
            orchestrator.stop()

    return 0


def run_daemon_mode(config_dir, pid_file='/var/run/camera-detection.pid'):
    """Run as daemon (background service)."""
    global orchestrator, logger

    # Check if already running
    if os.path.exists(pid_file):
        try:
            with open(pid_file, 'r') as f:
                old_pid = int(f.read().strip())

            # Check if process exists
            try:
                os.kill(old_pid, 0)
                logger.error(f"Daemon already running with PID {old_pid}")
                return 1
            except OSError:
                # Process doesn't exist, remove stale PID file
                os.remove(pid_file)
        except Exception as e:
            logger.warning(f"Error checking PID file: {e}")

    # Write PID file
    try:
        with open(pid_file, 'w') as f:
            f.write(str(os.getpid()))
    except Exception as e:
        logger.error(f"Cannot write PID file: {e}")
        return 1

    logger.info("="*70)
    logger.info(" Camera Detection System - Daemon Mode")
    logger.info("="*70)
    logger.info(f"PID: {os.getpid()}")

    # Initialize orchestrator
    orchestrator = OrchestratorAgent(config_dir=config_dir)

    # Start system
    if not orchestrator.start():
        logger.error("Failed to start system")
        os.remove(pid_file)
        return 1

    logger.info("Daemon started successfully")

    try:
        # Keep running indefinitely
        while True:
            time.sleep(300)  # 5 minutes

            # Log status
            status = orchestrator.get_status()
            logger.info(f"Daemon status: Uptime={status['uptime_seconds']:.0f}s, "
                       f"Frames={status['metrics']['frames_processed']}, "
                       f"Errors={status['metrics']['errors']}")

    except KeyboardInterrupt:
        logger.info("Daemon interrupt received")

    finally:
        orchestrator.stop()
        if os.path.exists(pid_file):
            os.remove(pid_file)
        logger.info("Daemon stopped")

    return 0


def main():
    """Main entry point."""
    global logger

    # Parse arguments
    parser = argparse.ArgumentParser(description='Camera Detection System')
    parser.add_argument('--api', action='store_true', help='Run with API server')
    parser.add_argument('--daemon', action='store_true', help='Run as daemon')
    parser.add_argument('--autostart', action='store_true', help='Auto-start detection (API mode only)')
    parser.add_argument('--host', default='0.0.0.0', help='API host (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=5000, help='API port (default: 5000)')
    parser.add_argument('--config-dir', default='/home/digioptics_od/camera-system/config',
                       help='Configuration directory')
    parser.add_argument('--pid-file', default='/var/run/camera-detection.pid',
                       help='PID file for daemon mode')

    args = parser.parse_args()

    # Setup logger
    log_dir = '/home/digioptics_od/camera-system/logs'
    os.makedirs(log_dir, exist_ok=True)
    logger = setup_logger('Main', os.path.join(log_dir, 'main.log'))

    # Verify config directory exists
    if not os.path.exists(args.config_dir):
        logger.error(f"Config directory not found: {args.config_dir}")
        print(f"Error: Config directory not found: {args.config_dir}")
        return 1

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run in selected mode
    if args.daemon:
        return run_daemon_mode(args.config_dir, args.pid_file)
    elif args.api:
        return run_api_mode(args.config_dir, args.host, args.port)
    else:
        return run_standalone(args.config_dir)


if __name__ == "__main__":
    sys.exit(main())
