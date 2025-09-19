# core/app.py
from PySide6.QtCore import QObject
from core.telemetry_manager import TelemetryManager
from core.uav_controller import UAVController
from core.mission_manager import MissionManager
from core.safety_monitor import SafetyMonitor
from core.uav_state import UAVState
import logging

class App(QObject):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.uav_states = {}  

        # Get logger using standard Python logging
        self.logger = logging.getLogger("REACT.App")
        self.logger.info("REACT Application starting...")

        # Initialize managers in dependency order
        self.telemetry_manager = TelemetryManager(self.uav_states, self.config)
        self.uav_controller = UAVController(self.uav_states, self.config)
        self.mission_manager = MissionManager(self.uav_states, self.config)
        self.safety_monitor = SafetyMonitor(self.uav_states, self.config)

        # Set up component connections
        self._setup_connections()

        self.logger.info("All managers initialized successfully")

    def _setup_connections(self):
        """Set up signal connections between components."""
        self.logger.info("Setting up component connections...")
        
        # Connect telemetry updates
        self.telemetry_manager.telemetry_updated.connect(self.on_telemetry_updated)
        
        # Connect UAVController commands to TelemetryManager
        self.uav_controller.command_requested.connect(self._handle_command_request)
        
        # Connect MissionManager upload requests to TelemetryManager
        self.mission_manager.mission_upload_requested.connect(self._handle_mission_upload_request)
        
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
        
        # Emit command result signal back to UAVController
        self.uav_controller.command_sent.emit(uav_id, command.get('type', 'unknown'))
        
        if not success:
            self.logger.warning(f"Command failed for {uav_id}: {command}")

    def _handle_mission_upload_request(self, uav_id, waypoint_file_path):
        """Handle mission upload requests from MissionManager."""
        self.logger.info(f"Processing mission upload request for {uav_id}: {waypoint_file_path}")
        
        success = self.telemetry_manager.load_mission(uav_id, waypoint_file_path)
        
        if success:
            # TODO: Get actual waypoint count from telemetry manager
            # For now, we'll let the mission manager handle this through other signals
            self.logger.info(f"Mission upload initiated for {uav_id}")
        else:
            self.mission_manager.mission_upload_failed(uav_id, "Upload failed")

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
            success = self.uav_controller.land_uav(uav_id)
            
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
            success = self.uav_controller.disarm_uav(uav_id)
            
        if not success:
            self.logger.error(f"Emergency disarm command failed for {uav_id}")

    def on_telemetry_updated(self, uav_id, telemetry_data):
        """Handle telemetry updates."""
        self.logger.debug(f"Telemetry update for {uav_id}: {telemetry_data}")
        
        # Forward telemetry to other managers that need it
        # SafetyMonitor and MissionManager will receive updates through shared uav_states

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

    def load_mission(self, uav_id, waypoint_file_path):
        """Load a mission to a UAV."""
        return self.mission_manager.load_mission_to_uav(uav_id, waypoint_file_path)

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





