# REACT - Robust Emergency Aircraft Control Terminal

A professional Ground Control Station (GCS) for UAV fleet management with dual telemetry architecture, comprehensive mission planning, and modern QML-based user interface.

## Features

- **Dual Telemetry Architecture**: Primary (MAVProxy routing) + Backup (direct SiK radio) connections with automatic failover
- **Multi-UAV Support**: Manage up to 10 UAVs simultaneously with individual selection and control
- **Real-time Monitoring**: Live UAV status, GPS, battery, flight data, and telemetry visualization
- **Advanced Mission Planning**: Load, execute, pause/resume from any waypoint, and abort missions with progress tracking
- **Interactive Map System**: OpenStreetMap and satellite imagery with flight path visualization and waypoint editing
- **Safety Systems**: Emergency stop, RTL, land commands, and automated safety monitoring with geofencing
- **Keyboard Shortcuts**: Full keyboard control for UAV selection (Ctrl+Alt+1-0), mode switching, and operations
- **Modern GUI**: Responsive QML-based interface with real-time updates and professional design
- **Comprehensive Logging**: Detailed mission logs and system monitoring with configurable log levels
- **Testing Suite**: Automated test scripts for validation of all core functionality

## System Requirements

### Supported Operating Systems
- **Windows**: 10/11 (64-bit)
- **Linux**: Ubuntu 18.04+, Debian 10+, CentOS 8+
- **macOS**: 10.15+ (Catalina or later)

### Python Version Requirements
- **Required**: Python 3.9 - 3.12
- **Recommended**: Python 3.12 (best PySide6 compatibility)
- **⚠️ Not Compatible**: Python 3.13+ (PySide6 compatibility issues)
- **⚠️ Avoid**: Windows Store Python (causes DLL loading issues)

### Hardware Requirements
- **CPU**: Intel Core i5 or AMD Ryzen 5 (minimum)
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 2GB free space
- **USB Ports**: 2x USB 2.0+ (for telemetry connections)
- **Network**: Internet connection for map tiles (optional offline mode available)

## Installation Guide

### Step 1: Install Python (Critical!)

#### Recommended: Standard Python from python.org

**Windows:**
```powershell
# Option A: Download from https://www.python.org/downloads/
# Choose Python 3.12.x and check "Add Python to PATH"

# Option B: Using Windows Package Manager
winget install Python.Python.3.12
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install python3.12 python3.12-venv python3.12-dev python3-pip
```

**Linux (CentOS/RHEL):**
```bash
sudo dnf install python3.12 python3.12-pip python3.12-devel
```

**macOS:**
```bash
# Using Homebrew
brew install python@3.12
```

#### ❌ What to Avoid
- **Windows Store Python**: Causes PySide6 DLL loading issues
- **Python 3.13+**: Limited PySide6 compatibility
- **System Python on Linux**: May lack development headers

### Step 2: Verify Python Installation

```bash
python --version
# Should show: Python 3.12.x

# On Linux/macOS, you may need:
python3.12 --version
```

**If using multiple Python versions:**
```bash
# Windows
py -3.12 --version

# Linux/macOS
python3.12 --version
```

### Step 3: Install REACT

#### Clone the Repository
```bash
git clone https://github.com/ZhiangChen/react.git
cd react/react/react
```

#### Create Virtual Environment (Recommended)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3.12 -m venv venv
source venv/bin/activate

# Multiple Python versions (Windows)
py -3.12 -m venv venv
venv\Scripts\activate
```

#### Install Dependencies
```bash
# Upgrade pip first
python -m pip install --upgrade pip

# Install REACT dependencies
pip install -r requirements.txt
```

### Step 4: Install Visual C++ Redistributables (Windows Only)

Download and install **Microsoft Visual C++ 2019/2022 Redistributable**:
- [Download Link](https://docs.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist)
- Install both x64 and x86 versions if unsure

### Step 5: Verify Installation

Run the comprehensive test suite:
```bash
python test_import.py     # Test all module imports
python test_qtlocation.py # Test Qt Location/mapping
python test_qml.py        # Test QML files
python test_all.py        # Run all tests
```

Expected output:
```
ALL TESTS PASSED! Your REACT environment is properly configured.
```

## Configuration

### Basic Configuration (config.yaml)

**Windows:**
```yaml
device_options:
  telem1_connection: "udp:127.0.0.1:14550"
  telem2_connection: "COM4"
```

**Linux:**
```yaml
device_options:
  telem1_connection: "udp:127.0.0.1:14550"
  telem2_connection: "/dev/ttyUSB1"
```

**macOS:**
```yaml
device_options:
  telem1_connection: "udp:127.0.0.1:14550"
  telem2_connection: "/dev/cu.usbserial-1234"
```

### Advanced Configuration Options

- **Telemetry Settings**: Configure baud rates, connection monitoring, and upload throttling
- **Map Configuration**: Choose between MapTiler, OpenStreetMap, or local tile server
- **NTRIP Settings**: RTK GPS correction data configuration
- **Safety Parameters**: Geofencing, altitude limits, and emergency protocols

## Usage

### Hardware Setup

1. **Connect Primary Telemetry** (USB to autopilot):
   ```bash
   # Install MAVProxy if not already installed
   pip install mavproxy

   # Start MAVProxy for telemetry routing
   # Linux/macOS:
   mavproxy.py --master=/dev/ttyUSB0 --baudrate 57600 --out=udp:127.0.0.1:14550

   # Windows:
   mavproxy.py --master=COM3 --baudrate 57600 --out=udp:127.0.0.1:14550
   ```

2. **Connect Backup Telemetry** (SiK radio pair):
   - Connect SiK radio to second USB port
   - Configure radio settings to match autopilot
   - Update `config.yaml` with correct port

### Starting the Application

#### Option 1: Launcher (Recommended)
```bash
# Navigate to application directory
cd react/react/react

# Start REACT with integrated tile server
python launcher.py
```

#### Option 2: Manual Start
```bash
# Navigate to application directory
cd react/react/react

# Activate virtual environment if using one
# Windows: venv\Scripts\activate
# Linux/macOS: source venv/bin/activate

# Start REACT
python main.py

# For specific Python version:
# Windows: py -3.12 main.py
# Linux/macOS: python3.12 main.py
```

### Keyboard Shortcuts

**UAV Selection:**
- `Ctrl+Alt+1-9`: Toggle selection of UAV 1-9
- `Ctrl+Alt+0`: Toggle selection of UAV 10
- `Ctrl+Alt+C`: Unselect all UAVs
- `Ctrl+Alt+R`: Reverse UAV selection

**Control Modes:**
- `Ctrl+Alt+A`: Switch to All UAVs mode
- `Ctrl+Alt+S`: Switch to Selected UAVs mode

### Mission Operations

1. **Upload Mission**: Load waypoint files (.waypoints format)
2. **Start Mission**: Choose starting waypoint (0 for beginning, or resume from specific waypoint)
3. **Monitor Progress**: Real-time mission status and UAV telemetry
4. **Emergency Controls**: Stop, RTL, or Land commands available

### Multi-UAV Operations

- Select individual UAVs or switch to fleet control mode
- Send commands to selected UAVs or entire fleet
- Monitor all UAVs simultaneously with individual status panels
- Synchronized mission execution across multiple aircraft

## Project Structure

```
react/
├── core/                    # Core application modules
│   ├── app.py              # Main application controller
│   ├── command_interface.py # UAV command handling
│   ├── mavlink_manager.py   # MAVLink protocol management
│   ├── mission_planner.py   # Mission planning and execution
│   ├── safety_monitor.py   # Safety monitoring and geofencing
│   └── uav_state.py        # UAV state management
├── qml/                    # QML user interface files
│   ├── MainWindow.qml      # Main application window
│   ├── UAVList.qml         # UAV selection and control panel
│   ├── MapContainer.qml    # Map display container
│   ├── MapView.qml         # Interactive map component
│   ├── MissionPlanner.qml  # Mission planning interface
│   └── SettingsDialog.qml  # Configuration settings
├── data/                   # Application data and logs
│   ├── logs/              # Mission and system logs
│   └── tiles/             # Cached map tiles
├── maps/                  # Map server and static files
├── utils/                 # Utility scripts and tools
├── config.yaml            # Application configuration
├── requirements.txt       # Python dependencies
├── main.py               # Application entry point
├── launcher.py           # Integrated launcher with tile server
└── test_*.py             # Test suite files
```

## Dependencies

### Core Dependencies
- **PySide6** (6.8.3+): Qt framework for GUI and QML
- **PyMAVLink** (2.4.37+): MAVLink protocol implementation
- **PyYAML** (6.0+): Configuration file parsing
- **pyserial** (3.5+): Serial communication for telemetry

### Map and Server Dependencies
- **FastAPI** (0.104.0+): Local tile server framework
- **Uvicorn** (0.24.0+): ASGI server for tile serving
- **aiohttp** (3.9.0+): Asynchronous HTTP client
- **aiofiles** (23.2.0+): Asynchronous file operations

### Qt Modules Used
- **QtCore**: Core Qt functionality and signals/slots
- **QtWidgets**: Widget framework for dialogs
- **QtQuick/QML**: Declarative UI framework
- **QtLocation**: Mapping and positioning services
- **QtPositioning**: GPS coordinate handling
- **QtWebEngine**: Web-based map rendering

## Testing

REACT includes a comprehensive test suite:

```bash
# Test all imports and basic functionality
python test_import.py

# Test Qt Location and mapping components
python test_qtlocation.py

# Test QML file loading and syntax
python test_qml.py

# Test mission resume functionality
python test_resume_mission.py

# Run all tests
python test_all.py
```

## Troubleshooting

### Common Issues

**Qt DLL Loading Errors (Windows):**
- Install Visual C++ Redistributables
- Use standard Python from python.org (not Windows Store)
- Ensure Python is in PATH

**Map Tiles Not Loading:**
- Check internet connection
- Verify API keys in config.yaml
- Use offline tile server mode

**Telemetry Connection Issues:**
- Verify COM port assignments
- Check baud rate settings
- Ensure MAVProxy is running for primary telemetry

**QML Rendering Problems:**
- Update graphics drivers
- Disable hardware acceleration if needed
- Check Qt version compatibility

### Logs and Debugging

All application logs are written to `data/logs/mission_log.txt`. Enable debug logging by modifying the logging configuration in `main.py`.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

This project is licensed under the terms specified in the LICENSE file.

## Support

For issues, questions, or contributions, please use the GitHub issue tracker or contact the maintainers.

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install python3.12 python3.12-venv python3.12-dev python3-pip
```

**Linux (CentOS/RHEL):**
```bash
sudo dnf install python3.12 python3.12-pip python3.12-devel
```

**macOS:**
```bash
# Using Homebrew
brew install python@3.12
```

#### ❌ What to Avoid
- **Windows Store Python**: Causes PySide6 DLL loading issues
- **Python 3.13+**: Limited PySide6 compatibility
- **System Python on Linux**: May lack development headers

### Step 2: Verify Python Installation

```bash
python --version
# Should show: Python 3.12.x

# On Linux/macOS, you may need:
python3.12 --version
```

**If using multiple Python versions:**
```bash
# Windows
py -3.12 --version

# Linux/macOS  
python3.12 --version
```

### Step 3: Install REACT

#### Clone the Repository
```bash
git clone https://github.com/ZhiangChen/react.git
cd react/react/react
```

#### Create Virtual Environment (Recommended)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3.12 -m venv venv
source venv/bin/activate

# Multiple Python versions (Windows)
py -3.12 -m venv venv
venv\Scripts\activate
```

#### Install Dependencies
```bash
# Upgrade pip first
python -m pip install --upgrade pip

# Install REACT dependencies
pip install -r requirements.txt
```

### Step 4: Install Visual C++ Redistributables (Windows Only)

Download and install **Microsoft Visual C++ 2019/2022 Redistributable**:
- [Download Link](https://docs.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist)
- Install both x64 and x86 versions if unsure

### Step 5: Verify Installation

Run the comprehensive test suite:
```bash
python test_import.py     # Test all module imports
python test_qtlocation.py # Test Qt Location/mapping
python test_qml.py        # Test QML files
python test_all.py        # Run all tests
```

Expected output:
```
ALL TESTS PASSED! Your REACT environment is properly configured.
```

## Configuration

### Basic Configuration (config.yaml)

**Windows:**
```yaml
device_options:
  telem1_connection: "udp:127.0.0.1:14550"
  telem2_connection: "COM4"
```

**Linux:**
```yaml
device_options:
  telem1_connection: "udp:127.0.0.1:14550" 
  telem2_connection: "/dev/ttyUSB1"
```

**macOS:**
```yaml
device_options:
  telem1_connection: "udp:127.0.0.1:14550"
  telem2_connection: "/dev/cu.usbserial-1234"
```

### Advanced Configuration Options

- **Telemetry Settings**: Configure baud rates, connection monitoring, and upload throttling
- **Map Configuration**: Choose between MapTiler, OpenStreetMap, or local tile server
- **NTRIP Settings**: RTK GPS correction data configuration
- **Safety Parameters**: Geofencing, altitude limits, and emergency protocols

## Usage

### Hardware Setup

1. **Connect Primary Telemetry** (USB to autopilot):
   ```bash
   # Install MAVProxy if not already installed
   pip install mavproxy
   
   # Start MAVProxy for telemetry routing
   # Linux/macOS:
   mavproxy.py --master=/dev/ttyUSB0 --baudrate 57600 --out=udp:127.0.0.1:14550
   
   # Windows:
   mavproxy.py --master=COM3 --baudrate 57600 --out=udp:127.0.0.1:14550
   ```

2. **Connect Backup Telemetry** (SiK radio pair):
   - Connect SiK radio to second USB port
   - Configure radio settings to match autopilot
   - Update `config.yaml` with correct port

### Starting the Application

#### Option 1: Launcher (Recommended)
```bash
# Navigate to application directory
cd react/react/react

# Start REACT with integrated tile server
python launcher.py
```

#### Option 2: Manual Start
```bash
# Navigate to application directory
cd react/react/react

# Activate virtual environment if using one
# Windows: venv\Scripts\activate
# Linux/macOS: source venv/bin/activate

# Start REACT
python main.py

# For specific Python version:
# Windows: py -3.12 main.py
# Linux/macOS: python3.12 main.py
```

### Keyboard Shortcuts

**UAV Selection:**
- `Ctrl+Alt+1-9`: Toggle selection of UAV 1-9
- `Ctrl+Alt+0`: Toggle selection of UAV 10
- `Ctrl+Alt+C`: Unselect all UAVs
- `Ctrl+Alt+R`: Reverse UAV selection

**Control Modes:**
- `Ctrl+Alt+A`: Switch to All UAVs mode
- `Ctrl+Alt+S`: Switch to Selected UAVs mode

### Mission Operations

1. **Upload Mission**: Load waypoint files (.waypoints format)
2. **Start Mission**: Choose starting waypoint (0 for beginning, or resume from specific waypoint)
3. **Monitor Progress**: Real-time mission status and UAV telemetry
4. **Emergency Controls**: Stop, RTL, or Land commands available

### Multi-UAV Operations

- Select individual UAVs or switch to fleet control mode
- Send commands to selected UAVs or entire fleet
- Monitor all UAVs simultaneously with individual status panels
- Synchronized mission execution across multiple aircraft

## Project Structure

```
react/
├── core/                    # Core application modules
│   ├── app.py              # Main application controller
│   ├── command_interface.py # UAV command handling
│   ├── mavlink_manager.py   # MAVLink protocol management
│   ├── mission_planner.py   # Mission planning and execution
│   ├── safety_monitor.py   # Safety monitoring and geofencing
│   └── uav_state.py        # UAV state management
├── qml/                    # QML user interface files
│   ├── MainWindow.qml      # Main application window
│   ├── UAVList.qml         # UAV selection and control panel
│   ├── MapContainer.qml    # Map display container
│   ├── MapView.qml         # Interactive map component
│   ├── MissionPlanner.qml  # Mission planning interface
│   └── SettingsDialog.qml  # Configuration settings
├── data/                   # Application data and logs
│   ├── logs/              # Mission and system logs
│   └── tiles/             # Cached map tiles
├── maps/                  # Map server and static files
├── utils/                 # Utility scripts and tools
├── config.yaml            # Application configuration
├── requirements.txt       # Python dependencies
├── main.py               # Application entry point
├── launcher.py           # Integrated launcher with tile server
└── test_*.py             # Test suite files
```

## Dependencies

### Core Dependencies
- **PySide6** (6.8.3+): Qt framework for GUI and QML
- **PyMAVLink** (2.4.37+): MAVLink protocol implementation  
- **PyYAML** (6.0+): Configuration file parsing
- **pyserial** (3.5+): Serial communication for telemetry

### Map and Server Dependencies  
- **FastAPI** (0.104.0+): Local tile server framework
- **Uvicorn** (0.24.0+): ASGI server for tile serving
- **aiohttp** (3.9.0+): Asynchronous HTTP client
- **aiofiles** (23.2.0+): Asynchronous file operations

### Qt Modules Used
- **QtCore**: Core Qt functionality and signals/slots
- **QtWidgets**: Widget framework for dialogs
- **QtQuick/QML**: Declarative UI framework
- **QtLocation**: Mapping and positioning services
- **QtPositioning**: GPS coordinate handling
- **QtWebEngine**: Web-based map rendering

## Testing

REACT includes a comprehensive test suite:

```bash
# Test all imports and basic functionality
python test_import.py

# Test Qt Location and mapping components
python test_qtlocation.py

# Test QML file loading and syntax
python test_qml.py

# Test mission resume functionality
python test_resume_mission.py

# Run all tests
python test_all.py
```

## Troubleshooting

### Common Issues

**Qt DLL Loading Errors (Windows):**
- Install Visual C++ Redistributables
- Use standard Python from python.org (not Windows Store)
- Ensure Python is in PATH

**Map Tiles Not Loading:**
- Check internet connection
- Verify API keys in config.yaml
- Use offline tile server mode

**Telemetry Connection Issues:**
- Verify COM port assignments
- Check baud rate settings
- Ensure MAVProxy is running for primary telemetry

**QML Rendering Problems:**
- Update graphics drivers
- Disable hardware acceleration if needed
- Check Qt version compatibility

### Logs and Debugging

All application logs are written to `data/logs/mission_log.txt`. Enable debug logging by modifying the logging configuration in `main.py`.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

This project is licensed under the terms specified in the LICENSE file.

## Support

For issues, questions, or contributions, please use the GitHub issue tracker or contact the maintainers.

