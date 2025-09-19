# REACT - Robust Emergency Aircraft Control Terminal

A professional Ground Control Station (GCS) for UAV fleet management with dual telemetry architecture, comprehensive mission planning, and modern QML-based user interface.

## Installation

### Prerequisites

- Python 3.8 or higher
- MAVLink-compatible autopilot (ArduPilot/PX4)  
- Ground station computer (Windows/Linux/macOS)

### Required Dependencies

```bash
pip install pymavlink PySide6 pyyaml
```

### Install REACT

```bash
git clone https://github.com/ZhiangChen/react.git
cd react/react
pip install -r requirements.txt
```

## Usage

### Configuration

Create `config.yaml` in the application directory:

```yaml
# Primary telemetry channel (via MAVProxy)
telemetry1:
  routed_to:
    protocol: "udp"
    udp_address: "127.0.0.1"
    udp_port: 14550
  input:
    protocol: "serial"
    port: "/dev/ttyUSB0"    # Linux/Mac
    # port: "COM3"          # Windows
    baud_rate: 57600

# Backup telemetry channel (direct SiK radio)
telemetry2:
  protocol: "serial"
  port: "/dev/ttyUSB1"      # Linux/Mac  
  # port: "COM4"            # Windows
  baud_rate: 57600
  connection_check: true

# Application settings
device_options:
  log_file_path: "data/logs/mission_log.txt"
```

### Starting the Application

```bash
cd react/react
python main.py
```

### Hardware Setup

1. **Connect Primary Telemetry** (USB to autopilot):
   ```bash
   # Start MAVProxy for telemetry routing
   mavproxy.py --master=/dev/ttyUSB0 --baudrate 57600 --out=udp:127.0.0.1:14550
   ```

2. **Connect Backup Telemetry** (SiK radio pair):
   - Connect SiK radio to second USB port
   - Configure radio settings to match autopilot
   - Update config.yaml with correct port

3. **Launch REACT**:
   ```bash
   python main.py
   ```

### Using the Interface

- **Map View**: Shows real-time UAV position, mission waypoints, and flight path
- **UAV Status Panel**: Displays telemetry data, battery, GPS, and connection status  
- **Control Buttons**: Arm/disarm, RTL, land, emergency stop
- **Menu Bar**: Load missions, control UAV, and access view options


