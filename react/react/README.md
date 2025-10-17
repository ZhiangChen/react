# REACT - Robust Emergency Aircraft Control Terminal

A professional Ground Control Station (GCS) for UAV fleet management with dual telemetry architecture, comprehensive mission planning, and modern QML-based user interface.


## Features

- **Dual Telemetry Architecture**: Primary (MAVProxy routing) + Backup (direct SiK radio) connections
- **Real-time Monitoring**: Live UAV status, GPS, battery, and flight data
- **Mission Planning**: Load, execute, pause/resume, and abort missions
- **Safety Systems**: Emergency stop, RTL, land, and automated safety monitoring
- **Interactive Map**: Map visualization with flight paths and waypoints
- **Multi-UAV Support**: Manage multiple UAVs simultaneously
- **Modern GUI**: QML-based interface with responsive design

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
- **Network**: Internet connection for map tiles

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


### Port Configuration Examples

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



## Dependencies

### Core Dependencies
- **PySide6** (6.8.3+): Qt framework for GUI
- **PyMAVLink** (2.4.37+): MAVLink protocol implementation  
- **PyYAML** (6.0+): Configuration file parsing
- **pyserial** (3.5+): Serial communication

### Optional Dependencies  
- **MAVProxy**: Telemetry routing and debugging
- **colorama**: Enhanced terminal output (test scripts)

### Qt Modules Used
- **QtCore**: Core Qt functionality
- **QtWidgets**: Widget framework
- **QtQuick**: QML engine
- **QtLocation**: Mapping and positioning
- **QtPositioning**: GPS coordinate handling

