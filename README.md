# Linear Actuator Control for Raspberry Pi

This project controls a linear actuator using a 2-channel relay module (SunFounder 2 Channel DC 5V Relay Module) connected to a Raspberry Pi.

## Hardware Requirements

- Raspberry Pi 2 (or compatible)
- SunFounder 2 Channel DC 5V Relay Module (Low-level trigger)
- Linear Actuator (DC powered)
- Appropriate power supply for the linear actuator
- Jumper wires for connections

## Wiring Instructions

### Power Supply Overview

**Important:** The Raspberry Pi's 5V is ONLY used to power the relay module's control circuitry. The linear actuator requires its own separate power supply (typically 12V, 24V, or whatever voltage your actuator requires). The relay module acts as an electrically isolated switch - the Pi controls the relay, and the relay switches the actuator's power supply.

### Relay Module to Raspberry Pi (Control Signals Only)

These connections power the relay module and provide control signals:

1. **Relay VCC** → Raspberry Pi **5V** (Pin 2) - *Powers the relay control circuitry only*
2. **Relay GND** → Raspberry Pi **GND** (Pin 6 or any GND)
3. **Relay IN1** (Channel 1 control) → Raspberry Pi **GPIO 18** (Pin 12)
4. **Relay IN2** (Channel 2 control) → Raspberry Pi **GPIO 23** (Pin 16)

### Linear Actuator Power Supply Wiring

The relay module acts as a polarity reverser for the actuator. You need a **separate power supply** for the actuator:

1. **Actuator Power Supply Positive** → Connect to **Common (COM)** terminal of both relay channels
2. **Actuator Wire 1** → Connect to **NO (Normally Open)** terminal of Relay Channel 1
3. **Actuator Wire 2** → Connect to **NO (Normally Open)** terminal of Relay Channel 2
4. **Actuator Power Supply Negative** → Connect to actuator's common/ground (if applicable)

**Important:** 
- The actuator power supply must match your actuator's voltage requirements (check actuator specifications)
- The relay can handle up to DC30V 10A - ensure your power supply and actuator don't exceed these limits
- The Pi's 5V is NOT connected to the actuator - only the separate power supply powers the actuator

### GPIO Pin Reference (Raspberry Pi 2)

```
Pin 2  → 5V (for relay VCC)
Pin 6  → GND
Pin 12 → GPIO 18 (Relay Channel 1)
Pin 16 → GPIO 23 (Relay Channel 2)
```

## Installation

1. Install the required Python library:
```bash
pip3 install -r requirements.txt
```

Or install directly:
```bash
pip3 install RPi.GPIO
```

2. Make the scripts executable (optional):
```bash
chmod +x actuator_control.py
chmod +x gpio_control.py
```

## Usage

Run the script:
```bash
python3 actuator_control.py
```

Or run directly:
```bash
./actuator_control.py
```

The script will:
1. Extend the actuator over 3 seconds
2. Immediately retract the actuator over 3 seconds
3. Wait 30 seconds
4. Repeat the cycle indefinitely

Press **Ctrl+C** to stop the script gracefully.

## GPIO Control Utility

A utility script `gpio_control.py` is included for manually controlling individual GPIO pins. This is useful for testing your wiring or controlling GPIO pins independently.

### Usage

Basic usage:
```bash
python3 gpio_control.py <GPIO_PIN> <STATUS>
```

Examples:
```bash
# Turn GPIO 18 ON (sets to HIGH)
python3 gpio_control.py 18 on

# Turn GPIO 18 OFF (sets to LOW)
python3 gpio_control.py 18 off

# For low-level trigger relay modules (like the SunFounder relay)
python3 gpio_control.py 18 on --low-level   # Sets GPIO to LOW (relay ON)
python3 gpio_control.py 18 off --low-level  # Sets GPIO to HIGH (relay OFF)

# Clean up GPIO after setting
python3 gpio_control.py 18 off --cleanup
```

### Options

- `<GPIO_PIN>`: GPIO pin number using BCM numbering (e.g., 18, 23)
- `<STATUS>`: `on` or `off`
- `--low-level`: Use low-level trigger logic (LOW=ON, HIGH=OFF). Required for low-level trigger relay modules.
- `--cleanup`: Clean up GPIO state after setting (default: leaves pin in set state)

### Help

View all options:
```bash
python3 gpio_control.py --help
```

## Configuration

You can modify the timing values in `actuator_control.py`:

```python
EXTEND_TIME = 3.0      # Time to extend actuator (seconds)
RETRACT_TIME = 3.0     # Time to retract actuator (seconds)
WAIT_TIME = 30.0       # Wait time between cycles (seconds)
```

You can also change the GPIO pins if needed:

```python
RELAY_CHANNEL_1 = 18  # GPIO pin for relay channel 1
RELAY_CHANNEL_2 = 23  # GPIO pin for relay channel 2
```

## How It Works

The relay module is a **low-level trigger** type, which means:
- **GPIO LOW (0)** = Relay ON
- **GPIO HIGH (1)** = Relay OFF

To control the actuator direction:
- **Extend**: Relay 1 ON, Relay 2 OFF (current flows one direction)
- **Retract**: Relay 1 OFF, Relay 2 ON (current flows opposite direction)
- **Stop**: Both relays OFF

## Troubleshooting

1. **Actuator doesn't move:**
   - Check all wiring connections
   - Verify power supply is connected and has correct voltage
   - Ensure relay module is powered (check LED indicators)
   - Test actuator directly with power supply to verify it works

2. **Wrong direction:**
   - Swap the actuator wires on the relay terminals

3. **Permission errors:**
   - Run with `sudo` if needed: `sudo python3 actuator_control.py`
   - Or add your user to the `gpio` group: `sudo usermod -a -G gpio $USER`

4. **GPIO warnings:**
   - The script suppresses GPIO warnings, but if you see issues, make sure no other programs are using the same GPIO pins

## Safety Notes

- Always disconnect power before making wiring changes
- Ensure the power supply can handle the actuator's current requirements
- The relay module can handle up to DC30V 10A - do not exceed these limits
- Test the wiring with a multimeter before connecting the actuator

