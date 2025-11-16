#!/usr/bin/env python3
"""
GPIO Control Script for Raspberry Pi
Simple utility to control a GPIO pin on or off via command line arguments.

Usage:
    python3 gpio_control.py <GPIO_PIN> <STATUS>
    
Examples:
    python3 gpio_control.py 18 on      # Turn GPIO 18 ON (HIGH)
    python3 gpio_control.py 18 off     # Turn GPIO 18 OFF (LOW)
    python3 gpio_control.py 23 on      # Turn GPIO 23 ON (HIGH)
    python3 gpio_control.py 23 off     # Turn GPIO 23 OFF (LOW)

Note: For low-level trigger relay modules (like the SunFounder relay),
      "on" sets GPIO to LOW and "off" sets GPIO to HIGH.
      Use --low-level flag for this behavior.
"""

import RPi.GPIO as GPIO
import argparse
import sys

# Default to standard GPIO behavior (HIGH = on, LOW = off)
# Use --low-level flag for low-level trigger devices (like relays)


def setup_gpio(pin, low_level=False):
    """Initialize GPIO pin as output"""
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(pin, GPIO.OUT)
    
    # Initialize to OFF state
    if low_level:
        GPIO.output(pin, GPIO.HIGH)  # HIGH = OFF for low-level trigger
    else:
        GPIO.output(pin, GPIO.LOW)   # LOW = OFF for standard GPIO


def set_gpio(pin, status, low_level=False):
    """
    Set GPIO pin to specified status
    
    Args:
        pin: GPIO pin number (BCM numbering)
        status: 'on' or 'off'
        low_level: If True, invert logic (for low-level trigger devices)
    """
    if status.lower() == 'on':
        if low_level:
            GPIO.output(pin, GPIO.LOW)   # LOW = ON for low-level trigger
            print("GPIO {} set to ON (LOW - for low-level trigger device)".format(pin))
        else:
            GPIO.output(pin, GPIO.HIGH)  # HIGH = ON for standard GPIO
            print("GPIO {} set to ON (HIGH)".format(pin))
    elif status.lower() == 'off':
        if low_level:
            GPIO.output(pin, GPIO.HIGH)  # HIGH = OFF for low-level trigger
            print("GPIO {} set to OFF (HIGH - for low-level trigger device)".format(pin))
        else:
            GPIO.output(pin, GPIO.LOW)   # LOW = OFF for standard GPIO
            print("GPIO {} set to OFF (LOW)".format(pin))
    else:
        print("Error: Status must be 'on' or 'off', got '{}'".format(status))
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Control a GPIO pin on or off',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s 18 on              # Turn GPIO 18 ON (HIGH)
  %(prog)s 18 off             # Turn GPIO 18 OFF (LOW)
  %(prog)s 23 on --low-level  # Turn GPIO 23 ON (LOW) for low-level trigger relay
  %(prog)s 23 off --low-level # Turn GPIO 23 OFF (HIGH) for low-level trigger relay
        """
    )
    
    parser.add_argument(
        'pin',
        type=int,
        help='GPIO pin number (BCM numbering, e.g., 18, 23)'
    )
    
    parser.add_argument(
        'status',
        choices=['on', 'off', 'ON', 'OFF'],
        help='Desired status: on or off'
    )
    
    parser.add_argument(
        '--low-level',
        action='store_true',
        help='Use low-level trigger logic (LOW=ON, HIGH=OFF). Use this for low-level trigger relay modules like the SunFounder relay.'
    )
    
    parser.add_argument(
        '--cleanup',
        action='store_true',
        help='Clean up GPIO after setting (default: leave pin in set state)'
    )
    
    args = parser.parse_args()
    
    # Validate GPIO pin number (common BCM GPIO pins are 2-27, but some are reserved)
    if args.pin < 2 or args.pin > 27:
        print("Warning: GPIO pin {} may not be valid. Common BCM GPIO pins are 2-27.".format(args.pin))
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(0)
    
    try:
        setup_gpio(args.pin, args.low_level)
        set_gpio(args.pin, args.status, args.low_level)
        
        if args.cleanup:
            GPIO.cleanup()
            print("GPIO cleaned up")
        else:
            print("GPIO {} is now set. Use --cleanup flag to reset GPIO state.".format(args.pin))
            
    except ValueError as e:
        print("Error: Invalid GPIO pin number - {}".format(e))
        sys.exit(1)
    except Exception as e:
        print("Error: {}".format(e))
        GPIO.cleanup()
        sys.exit(1)


if __name__ == "__main__":
    main()

