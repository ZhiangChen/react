# core/safety_monitor.py

import logging
import time
import threading
from PySide6.QtCore import QObject, Signal, QTimer

class SafetyMonitor(QObject):
    safety_alert = Signal(str, str)  # uav_id, alert_type
    emergency_action = Signal(str, str)  # uav_id, action

    def __init__(self, uav_states: dict, config: dict):
        super().__init__()
        self.uav_states = uav_states
        self.config = config
        self.running = False
        
        # Safety thresholds from config or defaults
        safety_config = config.get("safety", {})
        self.battery_failover_threshold = safety_config.get("battery_threshold", 20)  # Percentage
        self.communication_loss_threshold = safety_config.get("comm_timeout", 10)  # Seconds
        
        # Get logger using standard Python logging
        self.logger = logging.getLogger("REACT.SafetyMonitor")
        self.logger.info("Safety Monitor initialized")
        
        # Monitoring timer
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self._monitor_all_uavs)

    def start(self):
        """Start safety monitoring."""
        self.running = True
        self.monitor_timer.start(1000)  # Check every second
        self.logger.info("Safety monitoring started")

    def stop(self):
        """Stop safety monitoring."""
        self.running = False
        self.monitor_timer.stop()
        self.logger.info("Safety monitoring stopped")

    def _monitor_all_uavs(self):
        """Monitor all UAVs for safety issues."""
        if not self.running:
            return
            
        current_time = time.time()
        
        for uav_id, uav_state in self.uav_states.items():
            self._monitor_battery(uav_id, uav_state)
            self._monitor_communication(uav_id, uav_state, current_time)

    def _monitor_battery(self, uav_id, uav_state):
        """Monitor battery levels for failover."""
        battery_percent = uav_state.get_battery_percent()
        if battery_percent is not None and battery_percent < self.battery_failover_threshold:
            if battery_percent < 10:  # Critical level
                self.logger.critical(f"UAV {uav_id} critical battery: {battery_percent}%")
                self.emergency_action.emit(uav_id, "EMERGENCY_LAND")
            else:
                self.logger.warning(f"UAV {uav_id} low battery: {battery_percent}%")
                self.safety_alert.emit(uav_id, "LOW_BATTERY")

    def _monitor_communication(self, uav_id, uav_state, current_time):
        """Monitor communication status."""
        last_seen = uav_state.get_last_seen()
        if last_seen and (current_time - last_seen) > self.communication_loss_threshold:
            self.logger.error(f"UAV {uav_id} communication lost for {current_time - last_seen:.1f}s")
            self.safety_alert.emit(uav_id, "COMM_LOSS")

    def handle_emergency(self, uav_id, emergency_type):
        """Handle emergency situations."""
        self.logger.critical(f"Emergency for UAV {uav_id}: {emergency_type}")
        self.emergency_action.emit(uav_id, emergency_type)