#!/usr/bin/env python3
"""
Linear Actuator Control Script for Raspberry Pi
Controls a linear actuator using a 2-channel relay module.

IMPORTANT: The Raspberry Pi's 5V is ONLY used to power the relay module's
control circuitry. The linear actuator requires its own separate power supply
(typically 12V, 24V, etc.) that connects through the relay switch contacts.

Relay Module to Raspberry Pi (Control Only):
- Relay Channel 1: GPIO pin (default: 18)
- Relay Channel 2: GPIO pin (default: 23)
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
RELAY_CHANNEL_1 = 18  # GPIO pin for relay channel 1
RELAY_CHANNEL_2 = 23  # GPIO pin for relay channel 2

# Timing configuration (in seconds)
EXTEND_TIME = 3.0      # Time to extend actuator
RETRACT_TIME = 3.0     # Time to retract actuator
WAIT_TIME = 30.0       # Wait time between cycles

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
    
    # Initialize both relays to OFF (HIGH for low-level trigger)
    GPIO.output(RELAY_CHANNEL_1, RELAY_OFF)
    GPIO.output(RELAY_CHANNEL_2, RELAY_OFF)
    print("GPIO initialized")


def stop_actuator():
    """Stop the actuator by turning off both relays"""
    GPIO.output(RELAY_CHANNEL_1, RELAY_OFF)
    GPIO.output(RELAY_CHANNEL_2, RELAY_OFF)
    print("Actuator stopped")


def extend_actuator(duration):
    """
    Extend the actuator by activating relay 1 and deactivating relay 2
    
    Args:
        duration: Time in seconds to extend
    """
    print("Extending actuator for {} seconds...".format(duration))
    GPIO.output(RELAY_CHANNEL_1, RELAY_ON)   # Turn on relay 1
    GPIO.output(RELAY_CHANNEL_2, RELAY_OFF)  # Turn off relay 2
    
    # Control extension speed by pulsing if needed, or just wait
    time.sleep(duration)
    
    stop_actuator()
    print("Extension complete")


def retract_actuator(duration):
    """
    Retract the actuator by activating relay 2 and deactivating relay 1
    
    Args:
        duration: Time in seconds to retract
    """
    print("Retracting actuator for {} seconds...".format(duration))
    GPIO.output(RELAY_CHANNEL_1, RELAY_OFF)  # Turn off relay 1
    GPIO.output(RELAY_CHANNEL_2, RELAY_ON)   # Turn on relay 2
    
    # Control retraction speed by pulsing if needed, or just wait
    time.sleep(duration)
    
    stop_actuator()
    print("Retraction complete")


def run_cycle():
    """Execute one complete cycle: extend, retract, wait"""
    print("\n" + "="*50)
    print("Starting new cycle")
    print("="*50)
    
    # Extend actuator
    extend_actuator(EXTEND_TIME)
    
    # Small delay to ensure relay state change
    time.sleep(0.1)
    
    # Immediately retract actuator
    retract_actuator(RETRACT_TIME)
    
    # Wait before next cycle
    print("Waiting {} seconds before next cycle...".format(WAIT_TIME))
    time.sleep(WAIT_TIME)


def main():
    """Main control loop"""
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    print("Linear Actuator Control System")
    print("="*50)
    print("Relay Channel 1: GPIO {}".format(RELAY_CHANNEL_1))
    print("Relay Channel 2: GPIO {}".format(RELAY_CHANNEL_2))
    print("Extend time: {} seconds".format(EXTEND_TIME))
    print("Retract time: {} seconds".format(RETRACT_TIME))
    print("Wait time: {} seconds".format(WAIT_TIME))
    print("="*50)
    print("Press Ctrl+C to stop")
    print()
    
    try:
        setup_gpio()
        
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

