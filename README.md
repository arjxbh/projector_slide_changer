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
3. **Relay IN1** (Channel 1 control) → Raspberry Pi **GPIO 2** (Pin 3)
4. **Relay IN2** (Channel 2 control) → Raspberry Pi **GPIO 3** (Pin 5)

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
Pin 3  → GPIO 2 (Relay Channel 1)
Pin 5  → GPIO 3 (Relay Channel 2)
Pin 6  → GND
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

The script provides a REST API and web interface for controlling the actuator. When started, it:
1. Initializes GPIO pins
2. Waits for API commands to start cycling
3. When started via API, performs initial retraction (3 seconds)
4. Then cycles: extend (3s) → stop (100ms) → retract (3s) → wait (configurable)
5. Repeats the cycle until stopped via API

Press **Ctrl+C** to stop the script gracefully.

The web interface will be available at `http://<raspberry-pi-ip>:5000` or `http://localhost:5000`.

## Starting on Boot (systemd Service)

To automatically start the actuator control service when the Raspberry Pi boots:

1. **Copy the service file to systemd directory:**
   ```bash
   sudo cp actuator-control.service /etc/systemd/system/
   ```

2. **Edit the service file** (if your paths are different):
   ```bash
   sudo nano /etc/systemd/system/actuator-control.service
   ```
   
   Update these paths if needed:
   - `WorkingDirectory`: Path to your project directory
   - `ExecStart`: Full path to `actuator_control.py`
   - `User`: Your username (default is `pi`)

3. **Reload systemd to recognize the new service:**
   ```bash
   sudo systemctl daemon-reload
   ```

4. **Enable the service to start on boot:**
   ```bash
   sudo systemctl enable actuator-control.service
   ```

5. **Start the service now (optional):**
   ```bash
   sudo systemctl start actuator-control.service
   ```

6. **Check service status:**
   ```bash
   sudo systemctl status actuator-control.service
   ```

### Managing the Service

- **Stop the service:**
  ```bash
  sudo systemctl stop actuator-control.service
  ```

- **Start the service:**
  ```bash
  sudo systemctl start actuator-control.service
  ```

- **Restart the service:**
  ```bash
  sudo systemctl restart actuator-control.service
  ```

- **Disable auto-start on boot:**
  ```bash
  sudo systemctl disable actuator-control.service
  ```

- **View service logs:**
  ```bash
  sudo journalctl -u actuator-control.service -f
  ```

The service is configured to automatically restart if it crashes (with a 10-second delay).

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
INITIAL_RETRACT_TIME = 3.0   # Initial retraction on startup (seconds)
CYCLE_EXTEND_TIME = 3.0      # Extend time in cycle (seconds)
CYCLE_RETRACT_TIME = 3.0     # Retract time in cycle (seconds)
STOP_DELAY = 0.1             # Stop delay between extend/retract (seconds)
CYCLE_WAIT_TIME = 10.0       # Wait time between cycles (seconds, default)
```

Note: The cycle wait time can also be changed via the web interface or REST API.

You can also change the GPIO pins if needed:

```python
RELAY_CHANNEL_1 = 2   # GPIO pin for relay channel 1
RELAY_CHANNEL_2 = 3   # GPIO pin for relay channel 2
```

## How It Works

The relay module is a **low-level trigger** type, which means:
- **GPIO LOW (0)** = Relay ON
- **GPIO HIGH (1)** = Relay OFF

To control the actuator direction:
- **Extend**: Both GPIO pins ON (both relays ON) - current flows one direction
- **Retract**: Both GPIO pins OFF (both relays OFF) - current flows opposite direction
- **Stop**: GPIO pins in different states (one ON, one OFF) - no current flow

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

