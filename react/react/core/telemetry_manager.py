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
            
            time.sleep(0.005)  # Faster processing for responsive GUI (200Hz)

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
            # Handle both bytes and string types for msg.text
            if isinstance(msg.text, bytes):
                text = msg.text.decode('utf-8').strip()
            else:
                text = str(msg.text).strip()
            
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

    def _request_immediate_heartbeat(self, uav_id):
        """Request an immediate HEARTBEAT message from UAV for status update."""
        try:
            system_id = int(uav_id.split('_')[1]) if '_' in uav_id else 1
            
            if self._is_telem1_available():
                # Request immediate HEARTBEAT message
                self.telem1_connection.mav.command_long_send(
                    system_id,  # target_system
                    1,  # target_component
                    mavutil.mavlink.MAV_CMD_REQUEST_MESSAGE,  # command
                    0,  # confirmation
                    mavutil.mavlink.MAVLINK_MSG_ID_HEARTBEAT,  # param1: message ID
                    0, 0, 0, 0, 0, 0  # param2-7: unused
                )
                self.logger.debug(f"Requested immediate HEARTBEAT from {uav_id}")
                
        except Exception as e:
            self.logger.debug(f"Error requesting immediate heartbeat from {uav_id}: {e}")

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
            state.update_telemetry_protected(
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

        elif msg_type == "COMMAND_ACK":
            # Handle command acknowledgments for immediate UI feedback
            cmd_id = msg.command
            result = msg.result
            
            if cmd_id == mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM:
                if result == mavutil.mavlink.MAV_RESULT_ACCEPTED:
                    # ARM/DISARM command accepted - request immediate status update
                    self.logger.info(f"{uav_id} ARM/DISARM command accepted")
                    self._request_immediate_heartbeat(uav_id)
                    
                elif result == mavutil.mavlink.MAV_RESULT_IN_PROGRESS:
                    self.logger.debug(f"{uav_id} ARM/DISARM command in progress")
                    
                else:
                    # Command rejected
                    result_msgs = {
                        mavutil.mavlink.MAV_RESULT_DENIED: "Command denied",
                        mavutil.mavlink.MAV_RESULT_UNSUPPORTED: "Command unsupported",
                        mavutil.mavlink.MAV_RESULT_TEMPORARILY_REJECTED: "Temporarily rejected",
                        mavutil.mavlink.MAV_RESULT_FAILED: "Command failed"
                    }
                    error_msg = result_msgs.get(result, f"Unknown result {result}")
                    self.logger.warning(f"{uav_id} ARM/DISARM command rejected: {error_msg}")

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

    # Mission Control Methods
    def load_mission(self, uav_id, mission_file_path):
        """Load and upload mission from file to UAV.
        
        Args:
            uav_id (str): Target UAV identifier
            mission_file_path (str): Path to mission file (supports .waypoints, .mission formats)
            
        Returns:
            bool: True if mission was uploaded successfully, False otherwise
        """
        if uav_id not in self.uav_states:
            self.logger.error(f"Cannot load mission for unknown UAV: {uav_id}")
            return False
            
        if not os.path.exists(mission_file_path):
            self.logger.error(f"Mission file not found: {mission_file_path}")
            return False
            
        try:
            # Parse mission file
            waypoints = self._parse_mission_file(mission_file_path)
            if not waypoints:
                self.logger.error(f"No valid waypoints found in mission file: {mission_file_path}")
                return False
                
            self.logger.info(f"Loading mission with {len(waypoints)} waypoints to {uav_id}")
            
            # Step 1: Clear existing mission (best practice)
            self.logger.info(f"Clearing existing mission from {uav_id}")
            if not self.clear_mission(uav_id):
                self.logger.warning(f"Failed to clear existing mission from {uav_id}, continuing anyway")
            else:
                # Small delay after clearing to ensure it's processed
                time.sleep(0.5)
            
            # Step 2: Upload new mission to UAV
            success = self._upload_mission_to_uav(uav_id, waypoints)
            
            if success:
                self.logger.info(f"Mission successfully loaded to {uav_id} from {mission_file_path}")
            else:
                self.logger.error(f"Failed to upload mission to {uav_id}")
                
            return success
            
        except Exception as e:
            self.logger.error(f"Error loading mission file {mission_file_path}: {e}")
            return False

    def _parse_mission_file(self, mission_file_path):
        """Parse mission file and extract waypoints.
        
        Supports QGroundControl .mission format and ArduPilot .waypoints format.
        """
        waypoints = []
        
        try:
            with open(mission_file_path, 'r') as f:
                lines = f.readlines()
                
            # Check file format
            if mission_file_path.endswith('.mission'):
                # QGroundControl JSON format
                import json
                data = json.loads(''.join(lines))
                
                if 'mission' in data and 'items' in data['mission']:
                    for item in data['mission']['items']:
                        if item.get('type') == 'SimpleItem':
                            waypoint = {
                                'command': item.get('command', 16),  # MAV_CMD_NAV_WAYPOINT
                                'param1': item.get('param1', 0),
                                'param2': item.get('param2', 0), 
                                'param3': item.get('param3', 0),
                                'param4': item.get('param4', 0),
                                'x': item.get('coordinate', [0, 0])[0],  # latitude
                                'y': item.get('coordinate', [0, 0])[1],  # longitude
                                'z': item.get('coordinate', [0, 0, 0])[2] if len(item.get('coordinate', [])) > 2 else 0  # altitude
                            }
                            waypoints.append(waypoint)
                            
            else:
                # ArduPilot .waypoints format or generic format
                for i, line in enumerate(lines):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                        
                    # Skip header line in ArduPilot format
                    if i == 0 and line.startswith('QGC'):
                        continue
                        
                    parts = line.split('\t')
                    if len(parts) >= 12:
                        # Standard waypoint format: seq current frame command param1 param2 param3 param4 x y z autocontinue
                        waypoint = {
                            'seq': int(parts[0]),
                            'current': int(parts[1]),
                            'frame': int(parts[2]),
                            'command': int(parts[3]),
                            'param1': float(parts[4]),
                            'param2': float(parts[5]),
                            'param3': float(parts[6]),
                            'param4': float(parts[7]),
                            'x': float(parts[8]),     # latitude
                            'y': float(parts[9]),     # longitude
                            'z': float(parts[10]),    # altitude
                            'autocontinue': int(parts[11])
                        }
                        waypoints.append(waypoint)
                        
        except Exception as e:
            self.logger.error(f"Error parsing mission file {mission_file_path}: {e}")
            return []
            
        self.logger.debug(f"Parsed {len(waypoints)} waypoints from {mission_file_path}")
        return waypoints

    def _upload_mission_to_uav(self, uav_id, waypoints):
        """Upload waypoints to UAV using MAVLink mission protocol.
        
        Implements the full mission upload protocol:
        1. Send MISSION_COUNT
        2. Wait for MISSION_REQUEST messages
        3. Send MISSION_ITEM_INT for each requested waypoint
        4. Wait for MISSION_ACK confirmation
        """
        if not waypoints:
            return False
            
        try:
            system_id = int(uav_id.split('_')[1]) if '_' in uav_id else 1
            
            # Only use Telem1 for mission upload (requires bidirectional communication)
            if not (self._is_telem1_available() and self.is_connected(uav_id)):
                self.logger.error(f"Cannot upload mission to {uav_id} - Telem1 required for mission upload")
                return False
            
            # Mission upload state tracking
            upload_state = {
                'phase': 'count_sent',
                'waypoints_sent': 0,
                'waypoints_total': len(waypoints),
                'timeout_start': time.time(),
                'timeout_duration': 30.0,  # 30 second timeout
                'requests_received': set(),
                'ack_received': False
            }
            
            # Step 1: Send mission count
            self.logger.debug(f"Sending MISSION_COUNT: {len(waypoints)} waypoints to {uav_id}")
            self.telem1_connection.mav.mission_count_send(
                system_id,  # target_system
                1,  # target_component (autopilot)
                len(waypoints),  # count
                0  # mission_type (0 = mission waypoints)
            )
            
            # Step 2-4: Handle mission request/response protocol
            while upload_state['phase'] != 'complete' and not upload_state['ack_received']:
                current_time = time.time()
                
                # Check for timeout
                if current_time - upload_state['timeout_start'] > upload_state['timeout_duration']:
                    self.logger.error(f"Mission upload timeout for {uav_id} after {upload_state['timeout_duration']}s")
                    return False
                
                # Listen for mission protocol messages
                try:
                    msg = self.telem1_connection.recv_match(
                        type=['MISSION_REQUEST', 'MISSION_REQUEST_INT', 'MISSION_ACK'],
                        blocking=False,
                        timeout=0.1
                    )
                    
                    if msg and msg.get_srcSystem() == system_id:
                        msg_type = msg.get_type()
                        
                        if msg_type == 'MISSION_REQUEST' or msg_type == 'MISSION_REQUEST_INT':
                            # UAV is requesting a specific waypoint
                            seq = msg.seq
                            self.logger.debug(f"Received {msg_type} for waypoint {seq} from {uav_id}")
                            
                            if seq < len(waypoints):
                                upload_state['requests_received'].add(seq)
                                waypoint = waypoints[seq]
                                
                                # Send the requested waypoint
                                self.logger.debug(f"Sending waypoint {seq+1}/{len(waypoints)} to {uav_id}")
                                
                                self.telem1_connection.mav.mission_item_int_send(
                                    system_id,  # target_system
                                    1,  # target_component
                                    seq,  # seq (sequence number)
                                    waypoint.get('frame', mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT),
                                    waypoint.get('command', mavutil.mavlink.MAV_CMD_NAV_WAYPOINT),
                                    1 if seq == 0 else 0,  # current (1 for first waypoint, 0 for others)
                                    waypoint.get('autocontinue', 1),  # autocontinue
                                    waypoint.get('param1', 0),  # param1
                                    waypoint.get('param2', 0),  # param2  
                                    waypoint.get('param3', 0),  # param3
                                    waypoint.get('param4', 0),  # param4
                                    int(waypoint.get('x', 0) * 1e7),  # x (latitude * 1e7)
                                    int(waypoint.get('y', 0) * 1e7),  # y (longitude * 1e7)
                                    waypoint.get('z', 0),  # z (altitude)
                                    0  # mission_type
                                )
                                
                                upload_state['waypoints_sent'] += 1
                                
                                # Check if all waypoints have been requested
                                if len(upload_state['requests_received']) >= len(waypoints):
                                    upload_state['phase'] = 'waiting_ack'
                                    self.logger.debug(f"All waypoints sent to {uav_id}, waiting for ACK")
                                    
                            else:
                                self.logger.error(f"UAV {uav_id} requested invalid waypoint {seq} (max: {len(waypoints)-1})")
                                return False
                                
                        elif msg_type == 'MISSION_ACK':
                            # UAV is acknowledging mission upload
                            ack_type = msg.type
                            self.logger.debug(f"Received MISSION_ACK from {uav_id}: type={ack_type}")
                            
                            if ack_type == mavutil.mavlink.MAV_MISSION_ACCEPTED:
                                upload_state['ack_received'] = True
                                upload_state['phase'] = 'complete'
                                self.logger.info(f"Mission upload successful for {uav_id}")
                                return True
                            else:
                                # Mission upload failed
                                error_msgs = {
                                    mavutil.mavlink.MAV_MISSION_ERROR: "Generic error",
                                    mavutil.mavlink.MAV_MISSION_UNSUPPORTED_FRAME: "Unsupported coordinate frame",
                                    mavutil.mavlink.MAV_MISSION_UNSUPPORTED: "Unsupported mission command",
                                    mavutil.mavlink.MAV_MISSION_NO_SPACE: "No space left on device",
                                    mavutil.mavlink.MAV_MISSION_INVALID: "Invalid mission",
                                    mavutil.mavlink.MAV_MISSION_INVALID_PARAM1: "Invalid param1",
                                    mavutil.mavlink.MAV_MISSION_INVALID_PARAM2: "Invalid param2",
                                    mavutil.mavlink.MAV_MISSION_INVALID_PARAM3: "Invalid param3",
                                    mavutil.mavlink.MAV_MISSION_INVALID_PARAM4: "Invalid param4",
                                    mavutil.mavlink.MAV_MISSION_INVALID_PARAM5_X: "Invalid param5/X",
                                    mavutil.mavlink.MAV_MISSION_INVALID_PARAM6_Y: "Invalid param6/Y",
                                    mavutil.mavlink.MAV_MISSION_INVALID_PARAM7: "Invalid param7",
                                    mavutil.mavlink.MAV_MISSION_INVALID_SEQUENCE: "Invalid sequence",
                                    mavutil.mavlink.MAV_MISSION_DENIED: "Mission denied"
                                }
                                error_msg = error_msgs.get(ack_type, f"Unknown error {ack_type}")
                                self.logger.error(f"Mission upload failed for {uav_id}: {error_msg}")
                                return False
                                
                except Exception as e:
                    # Continue on receive errors, but log them
                    self.logger.debug(f"Error receiving mission protocol message: {e}")
                    
                # Small delay to prevent CPU hogging
                time.sleep(0.01)
            
            # If we get here, something went wrong
            self.logger.error(f"Mission upload incomplete for {uav_id}: phase={upload_state['phase']}, ack={upload_state['ack_received']}")
            return False
            
        except Exception as e:
            self.logger.error(f"Error uploading mission to {uav_id}: {e}")
            return False

    def start_mission(self, uav_id):
        """Start mission execution (mission must be pre-uploaded to UAV).
        
        This switches the UAV to AUTO mode to begin executing the uploaded mission.
        """
        if uav_id not in self.uav_states:
            self.logger.error(f"Cannot start mission for unknown UAV: {uav_id}")
            return False
            
        command = {
            'type': 'set_mode',
            'mode_number': 3,  # AUTO mode
            'mode_name': 'AUTO'
        }
        
        self.logger.info(f"Starting mission for {uav_id}")
        return self.send_command(uav_id, command)

    def pause_mission(self, uav_id):
        """Pause current mission execution.
        
        The UAV will hold position at current waypoint until resumed.
        """
        if uav_id not in self.uav_states:
            self.logger.error(f"Cannot pause mission for unknown UAV: {uav_id}")
            return False
            
        command = {
            'type': 'command_long',
            'command_id': mavutil.mavlink.MAV_CMD_DO_PAUSE_CONTINUE,
            'params': [0, 0, 0, 0, 0, 0, 0]  # param1=0 for pause
        }
        
        self.logger.info(f"Pausing mission for {uav_id}")
        return self.send_command(uav_id, command)

    def resume_mission(self, uav_id):
        """Resume paused mission execution.
        
        The UAV will continue from the current waypoint in the mission.
        """
        if uav_id not in self.uav_states:
            self.logger.error(f"Cannot resume mission for unknown UAV: {uav_id}")
            return False
            
        command = {
            'type': 'command_long',
            'command_id': mavutil.mavlink.MAV_CMD_DO_PAUSE_CONTINUE,
            'params': [1, 0, 0, 0, 0, 0, 0]  # param1=1 for continue/resume
        }
        
        self.logger.info(f"Resuming mission for {uav_id}")
        return self.send_command(uav_id, command)

    def abort_mission_rtl(self, uav_id):
        """Abort current mission and return to launch.
        
        This immediately stops mission execution and commands the UAV to return home.
        """
        if uav_id not in self.uav_states:
            self.logger.error(f"Cannot abort mission for unknown UAV: {uav_id}")
            return False
            
        command = {
            'type': 'set_mode',
            'mode_number': 6,  # RTL (Return to Launch) mode
            'mode_name': 'RTL'
        }
        
        self.logger.warning(f"Aborting mission for {uav_id} - switching to RTL")
        return self.send_command(uav_id, command)

    def abort_mission_loiter(self, uav_id):
        """Abort current mission and loiter at current position.
        
        This stops mission execution and holds the UAV at the current location.
        """
        if uav_id not in self.uav_states:
            self.logger.error(f"Cannot abort mission for unknown UAV: {uav_id}")
            return False
            
        command = {
            'type': 'set_mode',
            'mode_number': 5,  # LOITER mode
            'mode_name': 'LOITER'
        }
        
        self.logger.warning(f"Aborting mission for {uav_id} - switching to LOITER")
        return self.send_command(uav_id, command)

    def jump_to_waypoint(self, uav_id, waypoint_number, repeat_count=0):
        """Jump to specific waypoint in current mission.
        
        Args:
            uav_id (str): Target UAV identifier
            waypoint_number (int): Waypoint number to jump to (1-based)
            repeat_count (int): Number of times to repeat from this waypoint (0 = no repeat)
        """
        if uav_id not in self.uav_states:
            self.logger.error(f"Cannot jump waypoint for unknown UAV: {uav_id}")
            return False
            
        command = {
            'type': 'command_long',
            'command_id': mavutil.mavlink.MAV_CMD_DO_JUMP,
            'params': [waypoint_number, repeat_count, 0, 0, 0, 0, 0]
        }
        
        self.logger.info(f"Jumping to waypoint {waypoint_number} for {uav_id} (repeat: {repeat_count})")
        return self.send_command(uav_id, command)

    def set_current_waypoint(self, uav_id, waypoint_number):
        """Set the current waypoint in the mission sequence.
        
        Args:
            uav_id (str): Target UAV identifier
            waypoint_number (int): Waypoint number to set as current (0-based)
        """
        if uav_id not in self.uav_states:
            self.logger.error(f"Cannot set current waypoint for unknown UAV: {uav_id}")
            return False
            
        command = {
            'type': 'command_long',
            'command_id': mavutil.mavlink.MAV_CMD_DO_SET_MISSION_CURRENT,
            'params': [waypoint_number, 0, 0, 0, 0, 0, 0]  # param1=waypoint number
        }
        
        self.logger.info(f"Setting current waypoint to {waypoint_number} for {uav_id}")
        return self.send_command(uav_id, command)

    def clear_mission(self, uav_id):
        """Clear all waypoints from UAV mission.
        
        This removes all mission items from the UAV's memory.
        """
        if uav_id not in self.uav_states:
            self.logger.error(f"Cannot clear mission for unknown UAV: {uav_id}")
            return False
            
        try:
            system_id = int(uav_id.split('_')[1]) if '_' in uav_id else 1
            
            # Use the intelligent channel selection
            if self._is_telem1_available() and self.is_connected(uav_id):
                # Send via Telem1
                self.telem1_connection.mav.mission_clear_all_send(
                    system_id,  # target_system
                    1  # target_component (autopilot)
                )
                self.logger.info(f"Mission cleared for {uav_id} via Telem1")
                return True
                
            elif self.should_use_telem2(uav_id):
                # Send via Telem2 with redundancy
                for i in range(3):
                    self.telem2_connection.mav.mission_clear_all_send(
                        system_id,  # target_system
                        1  # target_component (autopilot)
                    )
                    time.sleep(0.025)  # Delay for SiK radio timing
                    
                self.logger.info(f"Mission cleared for {uav_id} via Telem2")
                return True
                
            else:
                self.logger.error(f"Cannot clear mission for {uav_id} - no telemetry channels available")
                return False
                
        except Exception as e:
            self.logger.error(f"Error clearing mission for {uav_id}: {e}")
            return False