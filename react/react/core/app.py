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

        # Initialize managers
        self.telemetry_manager = TelemetryManager(self.uav_states, self.config)
        self.mission_manager = MissionManager(self.uav_states, self.config)
        self.uav_controller = UAVController(self.uav_states, self.config)
        self.safety_monitor = SafetyMonitor(self.uav_states, self.config)

        self.logger.info("All managers initialized successfully")

    def start(self):
        """Start all managers and services."""
        self.logger.info("Starting REACT application...")
        
        # Start telemetry manager (this will start the background thread)
        self.telemetry_manager.start()
        
        # Start other services
        self.safety_monitor.start()
        
        self.logger.info("All services started successfully!")

    def stop(self):
        """Stop all managers and services."""
        self.logger.info("Stopping REACT application...")
        
        self.telemetry_manager.stop()
        self.safety_monitor.stop()
        
        self.logger.info("All services stopped.")

    def on_telemetry_updated(self, uav_id, telemetry_data):
        """Handle telemetry updates."""
        self.logger.debug(f"Telemetry update for {uav_id}: {telemetry_data}")





