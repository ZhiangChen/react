# Communication network

⬜ Telem1 on GCS1 (Mission Planner)  
⬜ Telem2 on GCS2 (REACT)  
✅ RC to multiple DSMX Remote Receivers  
⬜ Emlid RS3 to GCS1 and GCS2  
✅ Telemetry forwarding  

## Architecture
The system employs two GCSs: Mission Planner and REACT. **Telem1** uses P900 telemetry radio for bidirectional communication, routed to both GCS1 and GCS2 via MAVProxy. **Telem2** uses SiK Radio v3 for unidirectional communication from GCS2 to UAVs. 

Each UAV is equipped with a Spektrum radio receiver that supports multi-binding capability. The RC transmitter broadcasts commands to all UAVs simultaneously.Individual UAVs selectively respond to RC commands based on their current flight mode and the commands.

Emlid RS3 as a base station provides RTK corrections. Holybro H-RTK F9P Ultralight modules are equipped to each UAV. While the F9P modules lack onboard SD storage for directly logging raw GPS (RXM) data, raw GPS information can be written to the flight logger by enabling the `GPS_RAW_DATA` parameter. GPS base corrections are independently routed to both GCS1 and GCS2. 

GCS1 enables operators to control individual UAVs with the full functionality of Mission Planner. Operators can switch between different UAVs by accessing the `SysID` selection through the hidden menu shortcut `Ctrl+X`. GCS2 operates as a custom module built on MAVProxy and provides a GUI specifically designed for coordinated multi-UAV operations and emergency.


## GPS injection

## RC Binding
https://ardupilot.org/copter/docs/common-spektrum-rc.html#common-spektrum-rc 

## Telemetry Forwarding

[MAVProxy Documentation - Forwarding](https://ardupilot.org/mavproxy/docs/getting_started/forwarding.html)

MAVProxy is utilized for forwarding telemetry messages between the vehicle and multiple ground control applications.

**Download MAVProxy:** [Latest Release](https://firmware.ardupilot.org/Tools/MAVProxy/)

### Configuration

To route telemetry messages, use the following batch script:

```bat
@echo off
mavproxy.exe ^
  --master=COM5,57600 ^
  --out=udp:127.0.0.1:14550 ^
  --out=udp:127.0.0.1:14551 ^
  --streamrate=5
pause
```

**Parameters:**
- `COM5`: Telemetry serial port (adjust based on your system)
- `57600`: Default baud rate for telemetry communication
- `14550`: UDP port for Mission Planner
- `14551`: UDP port for REACT application
- `--streamrate=5`: Sets the telemetry stream rate to 5 Hz

This configuration enables simultaneous telemetry access for both Mission Planner and the REACT system.

Here is an example of listening and publishing mavlink messages in python: [react/utils/react_telem_example.py](../react/utils/react_telem_example.py)
