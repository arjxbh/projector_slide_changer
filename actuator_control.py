#!/usr/bin/env python3
"""
Linear Actuator Control Script for Raspberry Pi
Controls a linear actuator using a 2-channel relay module.

IMPORTANT: The Raspberry Pi's 5V is ONLY used to power the relay module's
control circuitry. The linear actuator requires its own separate power supply
(typically 12V, 24V, etc.) that connects through the relay switch contacts.

Relay Module to Raspberry Pi (Control Only):
- Relay Channel 1: GPIO pin 2
- Relay Channel 2: GPIO pin 3
- Relay GND: Raspberry Pi GND
- Relay VCC: Raspberry Pi 5V (powers relay control circuitry only)

Actuator Wiring (Separate Power Supply Required):
- Actuator Power Supply Positive: Common (COM) terminal of both relays
- Actuator wire 1: Relay 1 NO (Normally Open) terminal
- Actuator wire 2: Relay 2 NO (Normally Open) terminal
- Actuator Power Supply Negative: Connect to actuator common/ground
"""

import RPi.GPIO as GPIO
import time
import signal
import sys
import threading
from flask import Flask, jsonify, request, send_from_directory

# GPIO pin configuration
RELAY_CHANNEL_1 = 2   # GPIO pin for relay channel 1
RELAY_CHANNEL_2 = 3   # GPIO pin for relay channel 2

# Timing configuration (in seconds)
INITIAL_RETRACT_TIME = 3.0   # Initial retraction on startup
CYCLE_EXTEND_TIME = 3.0      # Extend time in cycle
CYCLE_RETRACT_TIME = 3.0     # Retract time in cycle
STOP_DELAY = 0.1             # Stop delay between extend/retract (100ms)
CYCLE_WAIT_TIME = 10.0       # Wait time between cycles

# Actuator control logic:
# Both GPIO ON (LOW for low-level trigger) = Retract
# Both GPIO OFF (HIGH for low-level trigger) = Extend
# Different states = Stop
# Since this is a LOW-level trigger relay:
# GPIO LOW (0) = Relay ON
# GPIO HIGH (1) = Relay OFF
RELAY_ON = GPIO.LOW
RELAY_OFF = GPIO.HIGH

# Global flags and state for API control
running = False  # Start with cycling stopped
cycle_wait_time = 10.0  # Default cycle wait time (will be set from CYCLE_WAIT_TIME)
cycle_thread = None
lock = threading.Lock()
gpio_initialized = False

# Flask app
app = Flask(__name__, static_folder='static')


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    global running
    print("\nStopping actuator control...")
    running = False
    stop_actuator()
    GPIO.cleanup()
    sys.exit(0)


def setup_gpio():
    """Initialize GPIO pins"""
    global gpio_initialized
    if gpio_initialized:
        return
    
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(RELAY_CHANNEL_1, GPIO.OUT)
    GPIO.setup(RELAY_CHANNEL_2, GPIO.OUT)
    
    # Initialize to stop state (different states)
    GPIO.output(RELAY_CHANNEL_1, RELAY_ON)
    GPIO.output(RELAY_CHANNEL_2, RELAY_OFF)
    gpio_initialized = True
    print("GPIO initialized")


def stop_actuator():
    """Stop the actuator by setting GPIO pins to different states"""
    GPIO.output(RELAY_CHANNEL_1, RELAY_ON)   # One ON
    GPIO.output(RELAY_CHANNEL_2, RELAY_OFF)  # One OFF
    print("Actuator stopped")


def extend_actuator(duration):
    """
    Extend the actuator by setting both GPIO pins to OFF (both relays OFF)
    
    Args:
        duration: Time in seconds to extend
    """
    print("Extending actuator for {} seconds...".format(duration))
    GPIO.output(RELAY_CHANNEL_1, RELAY_ON)  # Both ON = Extend
    GPIO.output(RELAY_CHANNEL_2, RELAY_ON)
    
    time.sleep(duration)
    
    stop_actuator()
    print("Extension complete")


def retract_actuator(duration):
    """
    Retract the actuator by setting both GPIO pins to ON (both relays ON)
    
    Args:
        duration: Time in seconds to retract
    """
    print("Retracting actuator for {} seconds...".format(duration))
    GPIO.output(RELAY_CHANNEL_1, RELAY_OFF)   # Both OFF = Retract
    GPIO.output(RELAY_CHANNEL_2, RELAY_OFF)
    
    time.sleep(duration)
    
    stop_actuator()
    print("Retraction complete")


def run_cycle():
    """Execute one complete cycle: extend, stop, retract, wait"""
    print("\n" + "="*50)
    print("Starting new cycle")
    print("="*50)
    
    # Extend actuator
    extend_actuator(CYCLE_EXTEND_TIME)
    
    # Stop for 100ms
    time.sleep(STOP_DELAY)
    
    # Retract actuator
    retract_actuator(CYCLE_RETRACT_TIME)
    
    # Wait before next cycle (use current cycle_wait_time)
    with lock:
        current_wait = cycle_wait_time
    print("Waiting {} seconds before next cycle...".format(current_wait))
    time.sleep(current_wait)


def actuator_control_loop():
    """Main actuator control loop that runs in a separate thread"""
    global running
    
    try:
        # GPIO should already be initialized, but ensure it is
        setup_gpio()
        
        # Initial retraction on startup
        print("Initial retraction...")
        retract_actuator(INITIAL_RETRACT_TIME)
        
        # Wait before starting cycle
        with lock:
            current_wait = cycle_wait_time
        print("Waiting {} seconds before starting cycle...".format(current_wait))
        time.sleep(current_wait)
        
        # Main loop
        cycle_count = 0
        while running:
            cycle_count += 1
            print("\nCycle #{}".format(cycle_count))
            run_cycle()
            
    except Exception as e:
        print("Error in actuator control loop: {}".format(e))
        stop_actuator()
        GPIO.cleanup()
        running = False


# Flask API Routes

@app.route('/')
def index():
    """Serve the web interface"""
    return send_from_directory('static', 'index.html')


@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current actuator status"""
    with lock:
        is_running = running
        wait_time = cycle_wait_time
    return jsonify({
        'running': is_running,
        'cycle_wait_time': wait_time
    })


@app.route('/api/start', methods=['POST'])
def start_cycling():
    """Start the actuator cycling"""
    global running, cycle_thread, cycle_wait_time
    
    with lock:
        if running:
            return jsonify({'success': False, 'message': 'Actuator is already running'}), 400
        
        running = True
        # Reset cycle_wait_time to default if needed
        if cycle_wait_time <= 0:
            cycle_wait_time = CYCLE_WAIT_TIME
    
    # Start the actuator control thread
    cycle_thread = threading.Thread(target=actuator_control_loop, daemon=True)
    cycle_thread.start()
    
    return jsonify({'success': True, 'message': 'Actuator cycling started'})


@app.route('/api/stop', methods=['POST'])
def stop_cycling():
    """Stop the actuator cycling"""
    global running
    
    with lock:
        if not running:
            return jsonify({'success': False, 'message': 'Actuator is not running'}), 400
        
        running = False
    
    # Stop the actuator immediately
    stop_actuator()
    
    return jsonify({'success': True, 'message': 'Actuator cycling stopped'})


@app.route('/api/cycle_wait_time', methods=['POST'])
def update_cycle_wait_time():
    """Update the time between cycles"""
    global cycle_wait_time
    
    data = request.get_json()
    if not data or 'time' not in data:
        return jsonify({'success': False, 'message': 'Missing "time" parameter'}), 400
    
    try:
        new_time = float(data['time'])
        if new_time < 0:
            return jsonify({'success': False, 'message': 'Time must be non-negative'}), 400
        
        with lock:
            cycle_wait_time = new_time
        
        return jsonify({
            'success': True,
            'message': 'Cycle wait time updated',
            'cycle_wait_time': cycle_wait_time
        })
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Invalid time value'}), 400


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    global running
    print("\nStopping actuator control...")
    with lock:
        running = False
    stop_actuator()
    GPIO.cleanup()
    sys.exit(0)


def main():
    """Main function to start the Flask server"""
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    # Initialize cycle_wait_time
    global cycle_wait_time
    cycle_wait_time = CYCLE_WAIT_TIME
    
    # Initialize GPIO at startup
    setup_gpio()
    
    print("Linear Actuator Control System with REST API")
    print("="*50)
    print("Relay Channel 1: GPIO {}".format(RELAY_CHANNEL_1))
    print("Relay Channel 2: GPIO {}".format(RELAY_CHANNEL_2))
    print("Initial retract: {} seconds".format(INITIAL_RETRACT_TIME))
    print("Cycle extend: {} seconds".format(CYCLE_EXTEND_TIME))
    print("Cycle retract: {} seconds".format(CYCLE_RETRACT_TIME))
    print("Stop delay: {} seconds".format(STOP_DELAY))
    print("Cycle wait: {} seconds (default)".format(CYCLE_WAIT_TIME))
    print("="*50)
    print("Web interface: http://0.0.0.0:5000")
    print("API endpoints:")
    print("  GET  /api/status - Get actuator status")
    print("  POST /api/start - Start actuator cycling")
    print("  POST /api/stop - Stop actuator cycling")
    print("  POST /api/cycle_wait_time - Update cycle wait time")
    print("="*50)
    print("Press Ctrl+C to stop")
    print()
    
    # Start Flask server
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)


if __name__ == "__main__":
    main()

