# core/telemetry_manager.py

from pymavlink import mavutil
from PySide6.QtCore import QObject, Signal, QTimer
from core.uav_state import UAVState
import threading
import time
import logging
import os

class TelemetryManager(QObject):
    telemetry_updated = Signal(str, dict)  # uav_id, telemetry data

    def __init__(self, uav_states: dict, config: dict):
        super().__init__()
        self.uav_states = uav_states
        self.config = config
        self.running = False
        self.telem1_connection = None  # Primary two-way communication
        self.telem2_connection = None  # Backup one-way communication
        self.thread = None
        self.discovered_uavs = set()  # Track discovered UAV system IDs
        self.uav_last_seen = {}  # Track last message time for each UAV
        self.uav_connection_timeout = 10  # seconds
        
        # Telem2 connection check variables (broadcast via Telem2)
        self.telem2_check_enabled = config.get("telemetry2", {}).get("connection_check", True)
        self.telem2_check_param = "SCR_USER1"  # Parameter name for connection check
        self.telem2_check_value = 0  # Counter value for parameter updates
        self.telem2_check_interval = 1.0  # seconds between parameter updates
        self.last_telem2_check = 0  # timestamp of last parameter send
        
        # Telem2 status tracking (monitored via Telem1 messages)
        self.uav_telem2_status = {}  # Track Telem2 connection status per UAV
        self.uav_telem2_last_update = {}  # Track last Telem2 status update per UAV
        self.telem2_status_timeout = 5.0  # seconds - if no status update, assume Telem2 lost
        
        # Get logger using standard Python logging
        self.logger = logging.getLogger("REACT.TelemetryManager")

    def setup_telem1(self):
        """Setup Telem1 connection based on config."""
        telem1_config = self.config.get("telemetry1", {})
        routed_to = telem1_config.get("routed_to", {})
        
        if routed_to.get("protocol") == "udp":
            connection_string = f"udp:{routed_to.get('udp_address', '127.0.0.1')}:{routed_to.get('udp_port', 14550)}"
        else:
            # Fallback to direct serial if no routing
            input_config = telem1_config.get("input", {})
            connection_string = f"{input_config.get('port', '/dev/ttyUSB0')}"
            
        try:
            # Create connection with source system and component IDs
            self.telem1_connection = mavutil.mavlink_connection(
                connection_string, 
                source_system=240, 
                source_component=190
            )
            self.logger.info(f"Telem1 connected to: {connection_string}")
            self.logger.info(f"Telem1 UAV discovery will happen continuously as messages arrive")
                
        except Exception as e:
            self.logger.error(f"Telem1 failed to connect: {e}")
            self.telem1_connection = None

    def setup_telem2(self):
        """Setup Telem2 connection for one-way communication (GCS -> UAV commands only)."""
        telem2_config = self.config.get("telemetry2", {})
        
        if telem2_config.get("protocol") == "serial":
            connection_string = telem2_config.get('port', '/dev/ttyUSB1')
            try:
                # Create connection for command sending only (one-way communication)
                self.telem2_connection = mavutil.mavlink_connection(
                    device=connection_string,
                    baud=telem2_config.get('baud_rate', 57600),
                    source_system=240,
                    source_component=190
                )
                self.logger.info(f"Telem2 connected for command sending: {connection_string}")
            except Exception as e:
                self.logger.error(f"Telem2 failed to connect: {e}")
                self.telem2_connection = None

    def start(self):
        """Start the background thread to read MAVLink messages."""
        self.setup_telem1()
        self.setup_telem2()
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        if self.telem1_connection:
            self.telem1_connection.close()
        if self.telem2_connection:
            self.telem2_connection.close()

    def _loop(self):
        """Main loop to poll MAVLink messages."""
        while self.running:
            # Primary communication via Telem1 (bidirectional)
            # UAV status is monitored via Telem1 messages only
            if self.telem1_connection:
                try:
                    msg = self.telem1_connection.recv_match(blocking=False)
                    if msg:
                        self._handle_telem1_message(msg)
                except Exception as e:
                    self.logger.error(f"Telem1 read error: {e}")
            
            # Periodically check UAV connection status
            self._check_uav_connection_status()
            
            # Periodically check Telem2 connection status (via Telem1 messages)
            self._check_telem2_status()
            
            # Periodically send Telem2 connection check (if enabled)
            self._check_telem2_connection()
            
            time.sleep(0.01)  # Avoid CPU hog

    def _is_telem1_available(self):
        """Check if Telem1 is available and responsive."""
        return self.telem1_connection is not None

    def _handle_telem1_message(self, msg):
        """Handle messages from Telem1 (primary channel)."""
        system_id = getattr(msg, 'get_srcSystem', lambda: None)()
        if system_id is None:
            return
            
        uav_id = f"UAV_{system_id}"
        current_time = time.time()
        
        # Continuously discover and add new UAVs
        if system_id not in self.discovered_uavs:
            self.discovered_uavs.add(system_id)
            self.uav_states[uav_id] = UAVState(uav_id)
            self.logger.info(f"New UAV discovered: {uav_id} (System ID: {system_id})")
        
        # Update last seen time for connection monitoring
        self.uav_last_seen[system_id] = current_time
        
        # Update UAV connection status
        if uav_id in self.uav_states:
            self.uav_states[uav_id].set_connected(True)
        
        self._process_mavlink_message(uav_id, msg)


    def _check_uav_connection_status(self):
        """Continuously monitor UAV connection status and detect disconnections."""
        current_time = time.time()
        
        for system_id in list(self.discovered_uavs):
            uav_id = f"UAV_{system_id}"
            last_seen = self.uav_last_seen.get(system_id, 0)
            time_since_last_msg = current_time - last_seen
            
            if uav_id in self.uav_states:
                # Check if UAV has timed out
                if time_since_last_msg > self.uav_connection_timeout:
                    # Mark as disconnected if not already
                    if self.uav_states[uav_id].is_connected():
                        self.uav_states[uav_id].set_connected(False)
                        self.logger.warning(f"UAV {uav_id} Telem1 connection lost (last seen {time_since_last_msg:.1f}s ago)")
                        
                        # Emit signal for UI updates
                        self.telemetry_updated.emit(uav_id, self.uav_states[uav_id].get_telemetry())

    def _check_telem2_connection(self):
        """Send periodic parameter updates via Telem2 to check connection status."""
        if not self.telem2_check_enabled or not self.telem2_connection:
            return
            
        current_time = time.time()
        
        # Check if it's time to send another connection check
        if current_time - self.last_telem2_check >= self.telem2_check_interval:
            self.last_telem2_check = current_time
            self.telem2_check_value += 1
            
            # Send parameter update to all discovered UAVs via Telem2
            for system_id in self.discovered_uavs:
                try:
                    self.telem2_connection.mav.param_set_send(
                        system_id,  # target_system
                        1,  # target_component (autopilot)
                        self.telem2_check_param.encode(),  # param_id
                        float(self.telem2_check_value),  # param_value
                        mavutil.mavlink.MAV_PARAM_TYPE_REAL32  # param_type
                    )
                    self.logger.debug(f"Sent Telem2 connection check to UAV_{system_id}: {self.telem2_check_param}={self.telem2_check_value}")
                except Exception as e:
                    self.logger.error(f"Failed to send Telem2 connection check to UAV_{system_id}: {e}")

    def _handle_statustext_message(self, uav_id, msg):
        """Handle STATUSTEXT messages to monitor Telem2 connection status."""
        try:
            text = msg.text.decode('utf-8').strip()
            system_id = int(uav_id.split('_')[1])
            current_time = time.time()
            
            # Look for Telem2 connection status messages from Lua script
            if "telem2 connection" in text.lower():
                if "restored" in text.lower() or "ok" in text.lower():
                    # Telem2 connection is working
                    if system_id not in self.uav_telem2_status or not self.uav_telem2_status[system_id]:
                        self.logger.info(f"{uav_id} Telem2 connection restored")
                    self.uav_telem2_status[system_id] = True
                    self.uav_telem2_last_update[system_id] = current_time
                    
                elif "lost" in text.lower():
                    # Telem2 connection lost
                    if system_id not in self.uav_telem2_status or self.uav_telem2_status[system_id]:
                        self.logger.warning(f"{uav_id} Telem2 connection lost")
                    self.uav_telem2_status[system_id] = False
                    self.uav_telem2_last_update[system_id] = current_time
                    
        except Exception as e:
            self.logger.error(f"Error processing STATUSTEXT for Telem2 status: {e}")

    def _check_telem2_status(self):
        """Check Telem2 connection status based on messages from UAVs via Telem1."""
        current_time = time.time()
        
        for system_id in list(self.discovered_uavs):
            uav_id = f"UAV_{system_id}"
            
            # Check if we have recent Telem2 status updates
            last_status_update = self.uav_telem2_last_update.get(system_id, 0)
            time_since_status = current_time - last_status_update
            
            # If no status update for too long, assume Telem2 connection unknown/lost
            if time_since_status > self.telem2_status_timeout:
                if system_id in self.uav_telem2_status and self.uav_telem2_status[system_id]:
                    self.logger.warning(f"{uav_id} Telem2 status unknown (no updates for {time_since_status:.1f}s)")
                    self.uav_telem2_status[system_id] = False
        
    def _process_mavlink_message(self, uav_id, msg):
        """Process MAVLink message and update UAV state."""
        state = self.uav_states.get(uav_id)
        if not state:
            return

        msg_type = msg.get_type()

        if msg_type == "GLOBAL_POSITION_INT":
            state.update_telemetry(
                latitude=msg.lat / 1e7,
                longitude=msg.lon / 1e7,
                altitude=msg.alt / 1000.0,  # MSL altitude in meters
                height=msg.relative_alt / 1000.0,  # AGL height in meters
                ground_speed=msg.vx / 100.0,  # Ground speed in m/s
                vertical_speed=msg.vz / 100.0,  # Vertical speed in m/s
                heading=msg.hdg / 100.0  # Heading in degrees
            )

        elif msg_type == "HEARTBEAT":
            state.update_telemetry(
                mode=mavutil.mode_string_v10(msg),
                armed=(msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED) != 0
            )

        elif msg_type == "ATTITUDE":
            state.update_telemetry(
                roll=msg.roll,  # Roll angle in radians
                pitch=msg.pitch,  # Pitch angle in radians
                yaw=msg.yaw  # Yaw angle in radians
            )

        elif msg_type == "SYS_STATUS":
            state.update_telemetry(
                battery_status=msg.battery_remaining  # Battery remaining percentage
            )

        elif msg_type == "VFR_HUD":
            # VFR_HUD provides airspeed and climb rate, but UAVState doesn't have airspeed field
            # Using vertical_speed from climb rate
            state.update_telemetry(
                vertical_speed=msg.climb  # Climb rate in m/s
            )

        elif msg_type == "GPS_RAW_INT":
            state.update_telemetry(
                gps_fix_type=msg.fix_type,
                satellites_visible=msg.satellites_visible
            )

        elif msg_type == "STATUSTEXT":
            # Monitor for Telem2 status messages from Lua script
            self._handle_statustext_message(uav_id, msg)

        # Emit signal to update GUI (or log)
        self.telemetry_updated.emit(uav_id, state.get_telemetry())

    def send_command_telem1(self, uav_id, command):
        """Send command via Telem1 (two-way communication)."""
        if not self.telem1_connection or uav_id not in self.uav_states:
            self.logger.warning(f"Cannot send Telem1 command - connection or UAV not available")
            return False
            
        try:
            # Extract system ID from uav_id (format: UAV_<system_id>)
            system_id = int(uav_id.split('_')[1]) if '_' in uav_id else 1
            
            if command.get('type') == 'set_mode':
                mode_number = command.get('mode_number', 0)
                self.logger.info(f"Sending mode change to {uav_id}: {command.get('mode_name', 'UNKNOWN')} ({mode_number})")
                
                self.telem1_connection.mav.set_mode_send(
                    system_id,
                    mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
                    mode_number
                )
                return True
                
            elif command.get('type') == 'command_long':
                cmd_id = command.get('command_id', 0)
                params = command.get('params', [0, 0, 0, 0, 0, 0, 0])
                
                self.logger.info(f"Sending command_long to {uav_id}: CMD_{cmd_id}")
                
                self.telem1_connection.mav.command_long_send(
                    system_id,
                    1,  # target_component (autopilot)
                    cmd_id,
                    0,  # confirmation
                    *params[:7]  # param1-7
                )
                return True
                
        except Exception as e:
            self.logger.error(f"Error sending Telem1 command: {e}")
            return False

    def send_command_telem2(self, uav_id, command):
        """Send command via Telem2 (backup one-way communication with broadcasting)."""
        if not self.telem2_connection:
            self.logger.warning(f"Cannot send Telem2 command - connection not available")
            return False
            
        if uav_id not in self.uav_states:
            self.logger.warning(f"Cannot send Telem2 command to unknown UAV: {uav_id}")
            return False
            
        try:
            # Extract system ID from uav_id (format: UAV_<system_id>)
            system_id = int(uav_id.split('_')[1]) if '_' in uav_id else 1
            
            if command.get('type') == 'set_mode':
                mode_number = command.get('mode_number', 0)
                mode_name = command.get('mode_name', 'UNKNOWN')
                
                self.logger.info(f"Broadcasting mode change to {uav_id} via Telem2: {mode_name} ({mode_number})")
                
                # Send command multiple times for reliability over SiK radio
                for i in range(3):
                    self.telem2_connection.mav.command_long_send(
                        system_id,  # target_system
                        1,  # target_component (autopilot)
                        mavutil.mavlink.MAV_CMD_DO_SET_MODE,  # command
                        0,  # confirmation
                        1,  # param1: mode (1=custom mode)
                        mode_number,  # param2: custom mode number
                        0, 0, 0, 0, 0  # param3-7: unused
                    )
                    time.sleep(0.025)  # Delay for SiK radio timing
                    
                self.logger.info(f"Telem2 mode command broadcasted to {uav_id}")
                return True
                
            elif command.get('type') == 'command_long':
                cmd_id = command.get('command_id', 0)
                params = command.get('params', [0, 0, 0, 0, 0, 0, 0])
                
                self.logger.info(f"Broadcasting command_long to {uav_id} via Telem2: CMD_{cmd_id}")
                
                # Send command multiple times for reliability
                for i in range(3):
                    self.telem2_connection.mav.command_long_send(
                        system_id,  # target_system
                        1,  # target_component (autopilot)
                        cmd_id,  # command
                        0,  # confirmation
                        *params[:7]  # param1-7
                    )
                    time.sleep(0.025)  # Delay for SiK radio timing
                    
                self.logger.info(f"Telem2 command_long broadcasted to {uav_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error sending Telem2 command to {uav_id}: {e}")
            return False
            
        self.logger.warning(f"Unsupported Telem2 command type: {command.get('type')}")
        return False

    def broadcast_emergency_command(self, command_type, **kwargs):
        """Broadcast emergency command to all UAVs via Telem2."""
        if not self.telem2_connection:
            self.logger.error("Cannot broadcast emergency command - Telem2 not available")
            return False
            
        self.logger.critical(f"Broadcasting emergency command to all UAVs: {command_type}")
        
        success_count = 0
        for system_id in self.discovered_uavs:
            uav_id = f"UAV_{system_id}"
            
            if command_type == "RTL":
                command = {
                    'type': 'set_mode',
                    'mode_number': 6,  # RTL mode
                    'mode_name': 'RTL'
                }
            elif command_type == "LAND":
                command = {
                    'type': 'set_mode', 
                    'mode_number': 9,  # LAND mode
                    'mode_name': 'LAND'
                }
            elif command_type == "DISARM":
                command = {
                    'type': 'command_long',
                    'command_id': mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                    'params': [0, 0, 0, 0, 0, 0, 0]  # param1=0 for disarm
                }
            else:
                self.logger.error(f"Unknown emergency command type: {command_type}")
                continue
                
            if self.send_command_telem2(uav_id, command):
                success_count += 1
                
        self.logger.critical(f"Emergency broadcast completed: {success_count}/{len(self.discovered_uavs)} UAVs")
        return success_count > 0


    def is_connected(self, uav_id):
        """Check if UAV is connected (monitored via Telem1 only)."""
        return uav_id in self.uav_states and self.uav_states[uav_id].is_connected()

    def get_telem2_status(self, uav_id):
        """Get Telem2 connection status for a specific UAV."""
        if uav_id not in self.uav_states:
            return False
            
        try:
            system_id = int(uav_id.split('_')[1]) if '_' in uav_id else 1
            return self.uav_telem2_status.get(system_id, False)
        except (ValueError, IndexError):
            return False

    def should_use_telem2(self, uav_id):
        """Determine if Telem2 should be used for sending commands to a UAV.
        
        Use Telem2 when:
        1. Telem1 is not available, OR
        2. UAV is not connected via Telem1, BUT Telem2 connection is good
        """
        if not self.telem2_connection:
            return False  # Telem2 not available
            
        telem1_available = self._is_telem1_available() and self.is_connected(uav_id)
        telem2_good = self.get_telem2_status(uav_id)
        
        # Prefer Telem1 if available, use Telem2 as backup
        if not telem1_available and telem2_good:
            return True
            
        return False

    def send_command(self, uav_id, command):
        """Send command via the best available telemetry channel.
        
        Args:
            uav_id (str): Target UAV identifier (format: UAV_<system_id>)
            command (dict): Command dictionary with 'type' and parameters
            
        Returns:
            bool: True if command was sent successfully, False otherwise
        """
        if uav_id not in self.uav_states:
            self.logger.error(f"Cannot send command to unknown UAV: {uav_id}")
            return False
            
        # Check if Telem1 is available and UAV is connected
        telem1_available = self._is_telem1_available() and self.is_connected(uav_id)
        telem2_available = self.should_use_telem2(uav_id)
        
        if telem1_available:
            # Primary channel: Use Telem1 (bidirectional, more reliable)
            self.logger.debug(f"Sending command to {uav_id} via Telem1 (primary)")
            return self.send_command_telem1(uav_id, command)
            
        elif telem2_available:
            # Backup channel: Use Telem2 (one-way, with broadcasting)
            self.logger.info(f"Sending command to {uav_id} via Telem2 (backup - Telem1 unavailable)")
            return self.send_command_telem2(uav_id, command)
            
        else:
            # No telemetry available
            self.logger.error(f"Cannot send command to {uav_id} - no telemetry channels available")
            self.logger.error(f"  Telem1 available: {self._is_telem1_available()}, UAV connected: {self.is_connected(uav_id)}")
            self.logger.error(f"  Telem2 available: {self.telem2_connection is not None}, Telem2 status: {self.get_telem2_status(uav_id)}")
            return False