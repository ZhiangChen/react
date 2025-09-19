# REACT Software Architecture

This document outlines the GUI design for REACT, a cross-platform GCS application to support multi-UAV mapping missions. The GCS is developed using PySide6, with a frontend powered by QML and a backend architecture built in Python. The system is designed to be modular, responsive, and compatible with multiple OS and platforms.

## Architecture Summary

### Frontend (QML)
- Built using QtQuick, QtLocation, QtPositioning, and QtQuick.Controls.
- Key components include:
  - **MapView**: Displays UAVs, paths, and waypoints using Map, MapQuickItem, and MapPolyline. Supports background maps via OpenStreetMap or MapTiler satellite tiles.
  - **MissionEditor**: Enables interactive mission definition with editable waypoint fields (latitude, longitude, altitude, hold time). Integrated with the backend MissionManager.
  - **UAVList**: Lists connected UAVs with telemetry data (e.g., battery, GPS, mode) and provides actions like arm/disarm, takeoff/land.
  - **SettingsDialog**: Allows entry of API keys, telemetry ports, tile server preferences, and device-specific options.

### Backend (Python/PySide6)
- Core logic includes:
  - **UAVController**: Manages UAV state, commands, and high-level behaviors such as arming, mode switching, and takeoff/landing.
  - **MissionManager**: Handles mission planning, editing, serialization (e.g., JSON, .plan, .mission), and validation.
  - **TelemetryManager**: Listens for real-time MAVLink telemetry, parses incoming data, and dispatches Qt signals to update the GUI.
  - **UAVState**: A per-drone model class that stores live telemetry data, including latitude, longitude, altitude, mode, and battery status. 
  - **SafetyMonitor**: Monitors mission safety by handling scenarios such as battery failover, geofence breaches, and communication loss.
- Interfaces with pymavlink and optionally MAVProxy for multi-vehicle routing and protocol bridging.


### Frontend and Backend Communication
- Utilizes Qt’s signal/slot system to connect Python and QML.
- QML listens to Python signals and connects to slots using `Connections {}`.

### Telemetry Flow
- Telemetry data flows from UAVs to the backend using MAVProxy.
- The backend processes telemetry and emits signals to update the QML frontend in real-time.
- **Telem1**: Serves as the primary telemetry channel, enabling two-way communication between the GCS and UAVs.
- **Telem2**: Acts as a secondary, one-way communication channel from the GCS to UAVs, activated only when Telem1 is unavailable. 
- The GCS must dynamically monitor both Telem1 and Telem2 connections to ensure communication safety.
- **TelemetryManager** tracks both channels and updates a per-drone status registry in UAVState.

## File Structure

```
react/
├── main.py
├── config.yaml
├── core/
├── core/
│   ├── app.py
│   ├── uav_controller.py
│   ├── mission_manager.py
│   ├── telemetry_manager.py
│   ├── uav_state.py
│   ├── safety_monitor.py
├── qml/
│   ├── MainWindow.qml
│   ├── MapView.qml
│   ├── MissionEditor.qml
│   ├── UAVList.qml
│   ├── SettingsDialog.qml
│   └── components/
├── plugins/  (e.g., RTK handler, survey grid generator)
├── data/     (missions/, logs/, cache/)
```

## Deployment Considerations
- Use tools like PySide6-deploy, briefcase, or pyqtdeploy for packaging.
- Avoid Qt WebEngine (not supported on iOS); prefer QtLocation.
- Ensure tile server access (e.g., MapTiler) supports mobile platforms.
- Separate configuration per OS via config.yaml or platform-specific overrides.

## Other Features
- Integration with RTK base stations.
- Survey grid generators and AOI coverage tools.
- Image mosaicking and footprint overlays.
- Mission file import/export (GeoJSON, .mission, .plan).
- Mission log.
