# Communication network

1. Telem1 on GCS1 
2. Telem2 on GCS2
3. RC to multiple DSMX Remote Receivers  
4. Emlid RS3 to GCS1
5. Telemetry forwarding




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
