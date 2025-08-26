# Communication network

⬜ Telem1 on GCS1 (Mission Planner)  
✅ Telem2 broadcasting on GCS2 (REACT)  
✅ Telem2 connection status  
✅ RC to multiple DSMX Remote Receivers  
⬜ Emlid RS3 to GCS1 and GCS2  
✅ Telemetry forwarding  

## Architecture
The system employs two GCSs: Mission Planner and REACT. **Telem1** uses P900 telemetry radio for bidirectional communication, routed to both GCS1 and GCS2 via MAVProxy. **Telem2** uses SiK Radio v3 for unidirectional communication from GCS2 to UAVs. 

Each UAV is equipped with a Spektrum radio receiver that supports multi-binding capability. The RC transmitter broadcasts commands to all UAVs simultaneously.Individual UAVs selectively respond to RC commands based on their current flight mode and the commands.

Emlid RS3 as a base station provides RTK corrections. Holybro H-RTK F9P Ultralight modules are equipped to each UAV. While the F9P modules lack onboard SD storage for directly logging raw GPS (RXM) data, raw GPS information can be written to the flight logger by enabling the `GPS_RAW_DATA` parameter. GPS base corrections are independently routed to both GCS1 and GCS2. 

GCS1 enables operators to control individual UAVs with the full functionality of Mission Planner. Operators can switch between different UAVs by accessing the `SysID` selection through the hidden menu shortcut `Ctrl+X`. GCS2 operates as a custom module built on MAVProxy and provides a GUI specifically designed for coordinated multi-UAV operations and emergency.


## Telem2 Broadcasting
Telem2 serves as the backup emergency telemetry channel for the REACT, using Holybro SiK Radio v3 modules. GCS2 connects to a master radio. Each UAV is equipped with a receiver radio. To ensure unidirectional communication from the ground station to the UAVs, the receiver radios must be configured with a `Duty Cycle` of 0, which disables transmission. Before setting duty cycle, bidirectional communication should be tested to ensure that the radio is functioning and the flight controller is set up correctly. 

To configure the duty cycle, PuTTY is required since Mission Planner cannot set the duty cycle to zero (though it can configure other values). In PuTTY, configure the serial port and baud rate, then click open. Enter `+++` to access AT command mode; a successful connection will display `OK`. Complete AT command documentation is available at: https://ardupilot.org/copter/docs/common-3dr-radio-advanced-configuration-and-technical-information.html   
E.g., show radio version:
```
ATI
```
show all user settable EEPROM parameters:
```
ATI5
```
display radio parameter number ‘n’:
```
ATSn?
```
set radio parameter number ‘n’ to ‘X’:
```
ATSn=X 
```
write current parameters to EEPROM:
```
AT&W
```
reboot the radio:
```
ATZ
```
reset all parameters to factory default:
```
AT&F
```
exit AT command mode:
```
ATO
```

Other important parameters include `Net ID` and `# of Channels`. All radios (the master and all receivers) must share the same Net ID. Individual commands are distinguished by the `SYSID_THISMAV` mavlink parameter. The `# of Channels` setting determines the number of channels used for frequency hopping between the minimum and maximum frequencies. Since this system uses broadcasting architecture, channel interference is not a concern. One single channel is enough. Additionally, frequency hopping is undesirable as it would require the master to repeat commands multiple times to ensure receivers don't miss signals during channel transitions. Therefore, `# of Channels` should be set to 1. 

The master radio uses default settings and must be configured with the same `Net ID` and `# of Channels` values as the receivers. 


A simple example of broadcasting commands for flight mode changes is available at: [react/utils/telem2_broadcast_example.py](../react/utils/telem2_broadcast_example.py). In this example, master radio connected to laptop via USB cable. A flight controller equipped with receiver radio is also connected to laptop via USB. The flight controller is monitored through Mission Planner for status verification. The Script demonstrates alternating flight modes between STABILIZE and LOITER 

## Telem2 Connection Monitoring
Although telem2 operates as unidirectional communication, REACT monitors its connection status via telem1. GCS2 periodically transmits parameter updates to modify the MAVLink parameter `SCR_USER1` on each UAV at a predefined frequency via telem2. Each UAV runs a Lua script that continuously monitors changes to the `SCR_USER1` parameter. If no parameter updates are detected within a specified timeout period, the script generates a "connection lost" alert message that is transmitted back to the ground station via telem1. We have examples of the lua script ([react/utils/telem2_connection_check.lua](../react/utils/telem2_connection_check.lua)) and the python script of requesting parameter modification ([react/utils/telem2_connection_check.py](../react/utils/telem2_connection_check.py)). 



## RC Binding
https://ardupilot.org/copter/docs/common-spektrum-rc.html#common-spektrum-rc 

## GPS Injection

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

Here is an example of listening and publishing mavlink messages in python: [react/utils/telem_routing_example.py](../react/utils/telem_routing_example.py)
