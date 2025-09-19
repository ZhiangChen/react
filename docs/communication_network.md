# Communication network

✅ Telem1 Point-to-Multipoint on GCS1 (REACT) and GCS2 (Mission Planner)  
✅ Telem2 broadcasting on GCS1  
✅ Telem2 connection status check  
✅ RC to multiple DSMX Remote Receivers  
✅ Emlid RS3 to GCS1 and GCS2  
✅ Telemetry forwarding  

## Architecture
The system employs two GCSs:  REACT and Mission Planner. **Telem1** uses P900 telemetry radio for bidirectional communication, routed to both GCS1 and GCS2 via MAVProxy. **Telem2** uses SiK Radio v3 for unidirectional communication from GCS1 to UAVs. 

Each UAV is equipped with a Spektrum radio receiver that supports multi-binding capability. The RC transmitter broadcasts commands to all UAVs simultaneously.Individual UAVs selectively respond to RC commands based on their current flight mode and the commands.

Emlid RS3 as a base station provides RTK corrections. Holybro H-RTK F9P Ultralight modules are equipped to each UAV. While the F9P modules lack onboard SD storage for directly logging raw GPS (RXM) data, raw GPS information can be written to the flight logger by enabling the `GPS_RAW_DATA` parameter. GPS base corrections are independently routed to both GCS1 and GCS2. 

GCS1 operates as a custom module built on MAVProxy and provides a GUI specifically designed for coordinated multi-UAV operations and emergency. GCS2 enables operators to control individual UAVs with the full functionality of Mission Planner. Operators can switch between different UAVs by accessing the `SysID` selection through the hidden menu shortcut `Ctrl+X`. 

## Telem1 Point-to-Multipoint Configuration
Telem1 serves as the primary telemetry channel for bidirectional communication between ground control stations and UAVs. The system utilizes Holybro Microhard P900 radios configured in point-to-multipoint (P2M) mode, with the ground control station equipped with a master radio and each UAV equipped with a dedicated remote radio.

**Critical Power and Wiring Requirements:** Both master and remote radios require external DC power (7-35V) during configuration and operation. However, all communication ports (telemetry and diagnosis) are serial interfaces that require voltages no greater than 5V. Extreme care must be taken during wiring installation for testing and operation. Ensure all connections are secure and clean, with no exposed pins that could cause short circuits. When using power distribution boards, seal all connections with electrical tape to prevent accidental contact with exposed pins. **Warning: Applying voltages greater than 5V to the serial ports will permanently damage the P900 modules.**

P2M configuration of Holybro P900 requires an FTDI serial-to-USB converter to interface with the **Diagnosis** port on the P900 modules. Radio setup is performed using `PicoConfig.exe` software. Testing has confirmed that version 1.7 operates reliably, while version 1.10 exhibits parameter configuration issues. [Version 1.7](../download/PicoConfig_1.7.zip) is included in the repository for convenience. Complete parameter configuration procedures are documented at: https://docs.holybro.com/radio/microhard-radio/point-to-multipoint-setup-with-microhard-radio

Make sure that `SYSID_THISMAV` is set with a unique value for each UAV. 

**Telemetry Efficiency:**   
  1. `SRx_` rate parameters can be set to reduce bandwidth load.
```
SRx_EXT_STAT   = 1    # Battery, EKF, system status at 1 Hz
SRx_POSITION   = 1    # GPS position at 1 Hz
SRx_EXTRA1     = 1    # Attitude at 1 Hz
SRx_EXTRA2     = 0    # Off (not needed unless debugging)
SRx_EXTRA3     = 0    # Off
SRx_RC_CHAN    = 1    # If you need RC feedback
SRx_RAW_SENS   = 0    # Off
SRx_PARAMS     = 0    # Off (lua checks parameters on FC but not needs to send them back to GCS)
SRx_ADSB       = 0    # Off
```
2. When two monopole antennas are too close together (especially on the same frequency band, like two P900s at 915 MHz), they have problems of mutual coupling, radiation pattern distortion, receiver desense / blocking, cross-interference in FHSS, and near-field effects. Therefore, we need to keep monopole antennas ≥ 1 wavelength (~33 cm for P900) apart for best isolation. An indicator is the telemetry signal strength at the top right corner of the flight data pannel in MP. 

3. Link Stats and MAVLink Inspector (Ctrl+f) provide essential bandwidth monitoring capabilities. P900 radios configured with P2M settings at 172.8 kbps wireless link rate can achieve approximately 20 KB/s effective throughput. 


## Telem2 Broadcasting
Telem2 serves as the backup emergency telemetry channel for the REACT, using Holybro SiK Radio v3 modules. GCS1 connects to a master radio. Each UAV is equipped with a receiver radio. To ensure unidirectional communication from the ground station to the UAVs, the receiver radios must be configured with a `Duty Cycle` of 0, which disables transmission. Before setting duty cycle, bidirectional communication should be tested to ensure that the radio is functioning and the flight controller is set up correctly. 

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
Although telem2 operates as unidirectional communication, REACT monitors its connection status via telem1. GCS1 periodically transmits parameter updates to modify the MAVLink parameter `SCR_USER1` on each UAV at a predefined frequency via telem2. Each UAV runs a Lua script that continuously monitors changes to the `SCR_USER1` parameter. If no parameter updates are detected within a specified timeout period, the script generates a "connection lost" alert message that is transmitted back to the ground station via telem1. We have examples of the lua script ([react/utils/telem2_connection_check.lua](../react/utils/telem2_connection_check.lua)) and the python script of requesting parameter modification ([react/utils/telem2_connection_check.py](../react/utils/telem2_connection_check.py)). 



## RC Binding
https://ardupilot.org/copter/docs/common-spektrum-rc.html#common-spektrum-rc 

## GPS Injection

To enable RTK corrections, first configure the **base output** as Local NTRIP. Access the base settings panel using the Emlid app or the configuration web interface (default IP: http://192.168.42.1/). Wait for the base to reach a converged state; if only a single solution is available but float status is desired, relocate the GPS to an open area for improved satellite reception. The base will begin streaming GPS correction signals only after convergence is achieved. "Convergence" refers to the base averaging its position over time after achieving a fix or float, depending on the availability of NTRIP corrections.


In the Wifi setting, activate hotspot. 

**Mission Planner**: 
Connect the GCS with the Emlid Hotspot. 

In MP SETUP->Optional Hardware->RTK/GPS Inject, connect MP via NTRIP:
```
http://reach:emlidreach@192.168.42.1:2101/REACH
```
This is an example of the url. The NTRIP information can be found on the Emlid base output page. 

After connecting NTRIP, the RTK GPS status should change to "Fixed". If the status remains "Float", relocate the UAV to an open area with better satellite reception. 

For telemetry configuration, setting the MAVLink type to raw data is not needed. 

**MAVProxy**: Connect the GCS with the Emlid hotspot. 

In the MAVProxy terminal, configure NTRIP:
```
module load ntrip
ntrip set caster 192.168.42.1
ntrip set port 2101
ntrip set mountpoint REACH
ntrip set username reach
ntrip set password emlidreach
ntrip start
```
Check the NTRIP status:
```
ntrip status
```
Check the GPS status:
```
status
```
The `fix_type` in `GPS_RAW_INT` should change from 4 to 6, where 4 indicates standard GPS and 6 indicates RTK Fix. This information can be verified via MAVLink Inspector in Mission Planner. 

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
