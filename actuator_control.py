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

# GPIO pin configuration
RELAY_CHANNEL_1 = 2   # GPIO pin for relay channel 1
RELAY_CHANNEL_2 = 3   # GPIO pin for relay channel 2

# Timing configuration (in seconds)
INITIAL_RETRACT_TIME = 3.0   # Initial retraction on startup
CYCLE_EXTEND_TIME = 2.0      # Extend time in cycle
CYCLE_RETRACT_TIME = 2.0     # Retract time in cycle
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

# Global flag for graceful shutdown
running = True


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
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(RELAY_CHANNEL_1, GPIO.OUT)
    GPIO.setup(RELAY_CHANNEL_2, GPIO.OUT)
    
    # Initialize to stop state (different states)
    GPIO.output(RELAY_CHANNEL_1, RELAY_ON)
    GPIO.output(RELAY_CHANNEL_2, RELAY_OFF)
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
    GPIO.output(RELAY_CHANNEL_1, RELAY_OFF)  # Both OFF = Extend
    GPIO.output(RELAY_CHANNEL_2, RELAY_OFF)
    
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
    GPIO.output(RELAY_CHANNEL_1, RELAY_ON)   # Both ON = Retract
    GPIO.output(RELAY_CHANNEL_2, RELAY_ON)
    
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
    
    # Wait before next cycle
    print("Waiting {} seconds before next cycle...".format(CYCLE_WAIT_TIME))
    time.sleep(CYCLE_WAIT_TIME)


def main():
    """Main control loop"""
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    print("Linear Actuator Control System")
    print("="*50)
    print("Relay Channel 1: GPIO {}".format(RELAY_CHANNEL_1))
    print("Relay Channel 2: GPIO {}".format(RELAY_CHANNEL_2))
    print("Initial retract: {} seconds".format(INITIAL_RETRACT_TIME))
    print("Cycle extend: {} seconds".format(CYCLE_EXTEND_TIME))
    print("Cycle retract: {} seconds".format(CYCLE_RETRACT_TIME))
    print("Stop delay: {} seconds".format(STOP_DELAY))
    print("Cycle wait: {} seconds".format(CYCLE_WAIT_TIME))
    print("="*50)
    print("Press Ctrl+C to stop")
    print()
    
    try:
        setup_gpio()
        
        # Initial retraction on startup
        print("Initial retraction...")
        retract_actuator(INITIAL_RETRACT_TIME)
        
        # Wait before starting cycle
        print("Waiting {} seconds before starting cycle...".format(CYCLE_WAIT_TIME))
        time.sleep(CYCLE_WAIT_TIME)
        
        # Main loop
        cycle_count = 0
        while running:
            cycle_count += 1
            print("\nCycle #{}".format(cycle_count))
            run_cycle()
            
    except Exception as e:
        print("Error: {}".format(e))
        stop_actuator()
        GPIO.cleanup()
        sys.exit(1)


if __name__ == "__main__":
    main()

