# core/app.py
from PySide6.QtCore import QObject, Slot, Signal, Property
from core.telemetry_manager import TelemetryManager
from core.uav_controller import UAVController
from core.mission_manager import MissionManager
from core.safety_monitor import SafetyMonitor
from core.uav_state import UAVState
from pymavlink import mavutil
import logging

class App(QObject):
    # Signal to notify QML of telemetry updates
    telemetry_changed = Signal(str, 'QVariant')  # uav_id, telemetry_data
    # Signal to notify QML when GCS home position changes
    gcs_home_changed = Signal(float, float, float)  # latitude, longitude, altitude
    # Signal to notify QML of mission upload results
    mission_upload_result = Signal(str, bool, str)  # uav_id, success, message
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.uav_states = {}  

        # Get logger using standard Python logging
        self.logger = logging.getLogger("REACT.App")
        self.logger.info("REACT Application starting...")

        # Initialize managers in dependency order
        self.telemetry_manager = TelemetryManager(self.uav_states, self.config)
        self._uav_controller = UAVController(self.uav_states, self.config)
        self.mission_manager = MissionManager(self.uav_states, self.config)
        self.safety_monitor = SafetyMonitor(self.uav_states, self.config)

        # Set up component connections
        self._setup_connections()

        self.logger.info("All managers initialized successfully")

    # QML Property to expose UAV controller
    @Property(QObject, constant=True)
    def uav_controller(self):
        return self._uav_controller

    def _setup_connections(self):
        """Set up signal connections between components."""
        self.logger.info("Setting up component connections...")
        
        # Connect telemetry updates
        self.telemetry_manager.telemetry_updated.connect(self.on_telemetry_updated)
        
        # Connect UAVController commands to TelemetryManager
        self._uav_controller.command_requested.connect(self._handle_command_request)
        
        # Connect MissionManager upload requests to TelemetryManager
        self.mission_manager.mission_upload_requested.connect(self._handle_mission_upload_request)
        
        # Connect MissionManager upload results to QML
        self.mission_manager.mission_upload_result.connect(self._handle_mission_upload_result)
        
        # Connect mission execution commands from MissionManager to TelemetryManager
        self.mission_manager.mission_started.connect(self._handle_mission_started)
        self.mission_manager.mission_paused.connect(self._handle_mission_paused)
        self.mission_manager.mission_resumed.connect(self._handle_mission_resumed)
        self.mission_manager.mission_aborted.connect(self._handle_mission_aborted)
        
        # Connect SafetyMonitor emergency signals to TelemetryManager
        self.safety_monitor.emergency_rtl_triggered.connect(self._handle_emergency_rtl)
        self.safety_monitor.emergency_land_triggered.connect(self._handle_emergency_land)
        self.safety_monitor.emergency_disarm_triggered.connect(self._handle_emergency_disarm)
        
        self.logger.info("Component connections established")

    def start(self):
        """Start all managers and services."""
        self.logger.info("Starting REACT application...")
        
        # Start telemetry manager first (this will start the background thread)
        self.telemetry_manager.start()
        
        # Start mission manager monitoring
        self.mission_manager.start()
        
        # Start safety monitor
        self.safety_monitor.start()
        
        self.logger.info("All services started successfully!")

    def stop(self):
        """Stop all managers and services."""
        self.logger.info("Stopping REACT application...")
        
        # Stop in reverse order
        self.safety_monitor.stop()
        self.mission_manager.stop()
        self.telemetry_manager.stop()
        
        self.logger.info("All services stopped.")

    # Signal handlers for component integration
    
    def _handle_command_request(self, uav_id, command):
        """Handle command requests from UAVController."""
        self.logger.debug(f"Processing command request for {uav_id}: {command.get('type', 'unknown')}")
        success = self.telemetry_manager.send_command(uav_id, command)
        
        # For ARM/DISARM commands, emit telemetry update to reflect optimistic GUI updates
        if command.get('command_id') == mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM:
            if uav_id in self.uav_states:
                self.telemetry_changed.emit(uav_id, self.uav_states[uav_id].get_telemetry())
        
        # Emit command result signal back to UAVController
        self._uav_controller.command_sent.emit(uav_id, command.get('type', 'unknown'))
        
        if not success:
            self.logger.warning(f"Command failed for {uav_id}: {command}")

    def _handle_mission_upload_request(self, uav_id, waypoint_file_path):
        """Handle mission upload requests from MissionManager."""
        self.logger.info(f"Processing mission upload request for {uav_id}: {waypoint_file_path}")
        
        success = self.telemetry_manager.load_mission(uav_id, waypoint_file_path)
        
        if success:
            self.logger.info(f"Mission upload successful for {uav_id}")
            # Emit success signal to QML
            self.mission_upload_result.emit(uav_id, True, "Mission uploaded successfully")
        else:
            self.logger.error(f"Mission upload failed for {uav_id}")
            # Emit failure signal to QML
            self.mission_upload_result.emit(uav_id, False, "Upload failed")
            self.mission_manager.mission_upload_failed(uav_id, "Upload failed")
    
    def _handle_mission_upload_result(self, uav_id, success, waypoints, message):
        """Forward mission upload results to QML."""
        self.logger.debug(f"Mission upload result for {uav_id}: success={success}, waypoints={waypoints}, message={message}")
        self.mission_upload_result.emit(uav_id, success, message)

    def _handle_mission_started(self, uav_id, mission_id):
        """Handle mission start requests."""
        self.logger.info(f"Starting mission {mission_id} for {uav_id}")
        success = self.telemetry_manager.start_mission(uav_id)
        
        if not success:
            self.mission_manager.abort_mission(uav_id, "Failed to start mission")

    def _handle_mission_paused(self, uav_id):
        """Handle mission pause requests."""
        self.logger.info(f"Pausing mission for {uav_id}")
        success = self.telemetry_manager.pause_mission(uav_id)
        
        if not success:
            self.logger.warning(f"Failed to pause mission for {uav_id}")

    def _handle_mission_resumed(self, uav_id):
        """Handle mission resume requests."""
        self.logger.info(f"Resuming mission for {uav_id}")
        success = self.telemetry_manager.resume_mission(uav_id)
        
        if not success:
            self.logger.warning(f"Failed to resume mission for {uav_id}")

    def _handle_mission_aborted(self, uav_id, reason):
        """Handle mission abort requests."""
        self.logger.warning(f"Aborting mission for {uav_id}: {reason}")
        success = self.telemetry_manager.abort_mission_rtl(uav_id)
        
        if not success:
            self.logger.error(f"Failed to abort mission for {uav_id}")

    def _handle_emergency_rtl(self, uav_id, reason):
        """Handle emergency RTL from SafetyMonitor."""
        self.logger.critical(f"Emergency RTL triggered for {uav_id}: {reason}")
        
        if uav_id == "ALL":
            # Emergency abort all missions
            self.mission_manager.emergency_abort_all()
            # Broadcast RTL to all UAVs
            success = self.telemetry_manager.broadcast_emergency_command("RTL")
        else:
            # Single UAV emergency
            self.mission_manager.abort_mission(uav_id, f"Emergency RTL: {reason}")
            success = self.telemetry_manager.abort_mission_rtl(uav_id)
            
        if not success:
            self.logger.error(f"Emergency RTL command failed for {uav_id}")

    def _handle_emergency_land(self, uav_id, reason):
        """Handle emergency land from SafetyMonitor."""
        self.logger.critical(f"Emergency land triggered for {uav_id}: {reason}")
        
        if uav_id == "ALL":
            # Emergency abort all missions
            self.mission_manager.emergency_abort_all()
            # Broadcast LAND to all UAVs
            success = self.telemetry_manager.broadcast_emergency_command("LAND")
        else:
            # Single UAV emergency
            self.mission_manager.abort_mission(uav_id, f"Emergency land: {reason}")
            success = self._uav_controller.land(uav_id)
            
        if not success:
            self.logger.error(f"Emergency land command failed for {uav_id}")

    def _handle_emergency_disarm(self, uav_id, reason):
        """Handle emergency disarm from SafetyMonitor."""
        self.logger.critical(f"Emergency disarm triggered for {uav_id}: {reason}")
        
        if uav_id == "ALL":
            # Emergency abort all missions
            self.mission_manager.emergency_abort_all()
            # Broadcast DISARM to all UAVs
            success = self.telemetry_manager.broadcast_emergency_command("DISARM")
        else:
            # Single UAV emergency
            self.mission_manager.abort_mission(uav_id, f"Emergency disarm: {reason}")
            success = self._uav_controller.disarm_uav(uav_id)
            
        if not success:
            self.logger.error(f"Emergency disarm command failed for {uav_id}")

    def on_telemetry_updated(self, uav_id, telemetry_data):
        """Handle telemetry updates and emit signal to QML."""
        self.logger.debug(f"Telemetry update for {uav_id}: {telemetry_data}")
        
        # Forward telemetry to other managers that need it
        # SafetyMonitor and MissionManager will receive updates through shared uav_states
        
        # Emit signal to update QML immediately
        self.telemetry_changed.emit(uav_id, telemetry_data)

    # Public API methods for external control
    
    def get_uav_status(self, uav_id):
        """Get current status of a UAV."""
        if uav_id in self.uav_states:
            return self.uav_states[uav_id].get_telemetry()
        return None

    def get_all_uav_status(self):
        """Get status of all UAVs."""
        return {uav_id: state.get_telemetry() for uav_id, state in self.uav_states.items()}

    def get_mission_status(self, uav_id):
        """Get mission status for a UAV."""
        return self.mission_manager.get_mission_status(uav_id)

    @Slot(str, str, result=bool)
    def load_mission(self, uav_id, waypoint_file_path):
        """Load a mission to a UAV."""
        return self.mission_manager.load_mission_to_uav(uav_id, waypoint_file_path)

    @Slot(str)
    def start_mission(self, uav_id):
        """Start mission execution for a UAV."""
        return self.mission_manager.start_mission(uav_id)

    def abort_mission(self, uav_id, reason="Manual abort"):
        """Abort mission for a UAV."""
        return self.mission_manager.abort_mission(uav_id, reason)

    def emergency_stop_all(self):
        """Emergency stop all UAVs."""
        self.logger.critical("Emergency stop all UAVs triggered")
        self.safety_monitor.emergency_abort_all()

    @Slot(str, result='QVariant')
    def get_uav_status(self, uav_id):
        """Get UAV status information for QML frontend."""
        if uav_id in self.uav_states:
            uav_state = self.uav_states[uav_id]
            return uav_state.get_telemetry()  # Use the new organized structure
        return None

    @Slot(result='QVariant')
    def getAllUAVs(self):
        """Get all UAV information for QML frontend."""
        uav_list = []
        for uav_id, uav_state in self.uav_states.items():
            uav_info = uav_state.get_telemetry()  # Use the new organized structure
            uav_list.append(uav_info)
        return uav_list

    @Slot(str, result='QVariant')
    def getHomePosition(self, uav_id):
        """Get home position for a specific UAV."""
        if uav_id in self.uav_states:
            uav_state = self.uav_states[uav_id]
            return {
                'latitude': uav_state.home_lat,
                'longitude': uav_state.home_lng,
                'altitude': uav_state.home_alt,
                'isValid': uav_state.home_lat != 0.0 or uav_state.home_lng != 0.0
            }
        return {'latitude': 0.0, 'longitude': 0.0, 'altitude': 0.0, 'isValid': False}
    
    @Slot(result='QVariant')
    def getGCSHomePosition(self):
        """Get global GCS home position (ground control station)."""
        gcs_home = self.config.get('gcs_home_position', {})
        if gcs_home and ('latitude' in gcs_home and 'longitude' in gcs_home):
            return {
                'latitude': gcs_home.get('latitude', 0.0),
                'longitude': gcs_home.get('longitude', 0.0),
                'altitude': gcs_home.get('altitude', 0.0),
                'isValid': True
            }
        # Fall back to default_home_position if GCS home not set
        default_home = self.config.get('default_home_position', {})
        has_default = default_home.get('latitude') is not None and default_home.get('longitude') is not None
        return {
            'latitude': default_home.get('latitude', 0.0),
            'longitude': default_home.get('longitude', 0.0),
            'altitude': default_home.get('altitude', 0.0),
            'isValid': has_default
        }
    
    @Slot(float, float, float)
    def setGCSHomePosition(self, latitude, longitude, altitude=0.0):
        """Set global GCS home position (ground control station)."""
        self.logger.info(f"Setting GCS home position to: {latitude}, {longitude}, {altitude}")
        self.config['gcs_home_position'] = {
            'latitude': latitude,
            'longitude': longitude,
            'altitude': altitude
        }
        # Emit signal to notify QML that GCS home has changed
        self.gcs_home_changed.emit(latitude, longitude, altitude)
        self.logger.info("GCS home position updated and signal emitted")

    @Slot(str, result='QVariant')
    def getWaypoints(self, uav_id):
        """Get mission waypoints for a specific UAV."""
        # Return empty array for now - can be implemented when mission planning is added
        return []

    @Slot(result='QVariant')
    def getGeofences(self):
        """Get all geofences."""
        # Return empty array for now - can be implemented when geofencing is added
        return []

    @Slot(str, result='QVariant')
    def getUAVPosition(self, uav_id):
        """Get UAV position for QML."""
        if uav_id in self.uav_states:
            uav_state = self.uav_states[uav_id]
            return {
                'latitude': uav_state.latitude,
                'longitude': uav_state.longitude,
                'altitude': uav_state.altitude,
                'isValid': uav_state.gps_fix_type >= 2
            }
        return {'latitude': 0.0, 'longitude': 0.0, 'altitude': 0.0, 'isValid': False}

    @Slot(str, result=float)
    def getUAVHeading(self, uav_id):
        """Get UAV heading for QML."""
        if uav_id in self.uav_states:
            return self.uav_states[uav_id].heading
        return 0.0

    @Slot(str, result=str)
    def getUAVMode(self, uav_id):
        """Get UAV mode for QML."""
        if uav_id in self.uav_states:
            return self.uav_states[uav_id].mode
        return "UNKNOWN"

    @Slot(str, result=str)
    def getArmedState(self, uav_id):
        """Get UAV armed state for QML."""
        if uav_id in self.uav_states:
            return "ARMED" if self.uav_states[uav_id].armed else "DISARMED"
        return "DISARMED"

    @Slot(result=int)
    def getMaxUAVs(self):
        """Get maximum number of UAVs from config, reloading config each time for dynamic updates."""
        import yaml
        try:
            with open("config.yaml", "r") as f:
                current_config = yaml.safe_load(f)
            return current_config.get("device_options", {}).get("max_uavs", 1)
        except Exception as e:
            self.logger.warning(f"Failed to reload config for max_uavs: {e}")
            # Fall back to cached config
            return self.config.get("device_options", {}).get("max_uavs", 1)


