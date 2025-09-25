# core/safety_monitor.py

import logging
import time
import threading
import math
from PySide6.QtCore import QObject, Signal, QTimer
from enum import Enum

class SafetyLevel(Enum):
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class AlertType(Enum):
    LOW_BATTERY = "low_battery"
    CRITICAL_BATTERY = "critical_battery"
    COMM_LOSS = "comm_loss"
    GPS_LOSS = "gps_loss"
    ALTITUDE_VIOLATION = "altitude_violation"
    EXCESSIVE_SPEED = "excessive_speed"
    ATTITUDE_EXTREME = "attitude_extreme"
    MISSION_TIMEOUT = "mission_timeout"
    SYSTEM_ERROR = "system_error"

class SafetyMonitor(QObject):
    # Safety signals
    safety_alert = Signal(str, str, str)  # uav_id, alert_type, message
    emergency_action = Signal(str, str)   # uav_id, action_type
    safety_status_changed = Signal(str, str)  # uav_id, safety_level
    
    # Specific emergency signals expected by App
    emergency_rtl_triggered = Signal(str, str)    # uav_id, reason
    emergency_land_triggered = Signal(str, str)   # uav_id, reason
    emergency_disarm_triggered = Signal(str, str) # uav_id, reason
    
    def __init__(self, uav_states: dict, config: dict):
        super().__init__()
        self.uav_states = uav_states
        self.config = config
        self.running = False
        
        # Safety thresholds from config or defaults
        safety_config = config.get("safety", {})
        self.battery_warning_threshold = safety_config.get("battery_warning", 30)  # %
        self.battery_critical_threshold = safety_config.get("battery_critical", 20)  # %
        self.battery_emergency_threshold = safety_config.get("battery_emergency", 10)  # %
        self.communication_timeout = safety_config.get("comm_timeout", 10)  # seconds
        self.gps_timeout = safety_config.get("gps_timeout", 5)  # seconds
        self.max_altitude = safety_config.get("max_altitude", 120)  # meters AGL
        self.min_altitude = safety_config.get("min_altitude", 5)  # meters AGL
        self.max_speed = safety_config.get("max_speed", 15)  # m/s
        self.max_roll_pitch = safety_config.get("max_roll_pitch", 45)  # degrees
        self.mission_timeout = safety_config.get("mission_timeout", 1800)  # seconds (30 min)
        
        # Safety state tracking
        self.uav_safety_status = {}  # uav_id -> SafetyLevel
        self.alert_history = {}  # uav_id -> list of alerts
        self.last_alert_time = {}  # uav_id -> dict of alert_type -> timestamp
        self.mission_start_times = {}  # uav_id -> start_timestamp
        
        # Alert suppression (prevent spam)
        self.alert_cooldown = 30  # seconds between same alert types
        
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

    def set_mission_started(self, uav_id):
        """Mark that a mission has started for a UAV."""
        self.mission_start_times[uav_id] = time.time()
        self.logger.info(f"Mission started tracking for {uav_id}")

    def set_mission_ended(self, uav_id):
        """Mark that a mission has ended for a UAV."""
        if uav_id in self.mission_start_times:
            del self.mission_start_times[uav_id]
        self.logger.info(f"Mission ended tracking for {uav_id}")

    def _monitor_all_uavs(self):
        """Monitor all UAVs for safety issues."""
        if not self.running:
            return
            
        current_time = time.time()
        
        for uav_id, uav_state in self.uav_states.items():
            # Initialize safety status if not exists
            if uav_id not in self.uav_safety_status:
                self.uav_safety_status[uav_id] = SafetyLevel.NORMAL
                self.alert_history[uav_id] = []
                self.last_alert_time[uav_id] = {}
            
            # Perform all safety checks
            self._monitor_battery(uav_id, uav_state, current_time)
            self._monitor_communication(uav_id, uav_state, current_time)
            self._monitor_gps(uav_id, uav_state, current_time)
            self._monitor_altitude(uav_id, uav_state, current_time)
            self._monitor_speed(uav_id, uav_state, current_time)
            self._monitor_attitude(uav_id, uav_state, current_time)
            self._monitor_mission_timeout(uav_id, uav_state, current_time)
            
            # Update overall safety status
            self._update_safety_status(uav_id)

    def _monitor_battery(self, uav_id, uav_state, current_time):
        """Monitor battery levels for warnings and emergencies."""
        battery_percent = uav_state.battery_status
        
        if battery_percent <= self.battery_emergency_threshold:
            if self._should_send_alert(uav_id, AlertType.CRITICAL_BATTERY, current_time):
                self._send_alert(uav_id, AlertType.CRITICAL_BATTERY, 
                               f"CRITICAL battery: {battery_percent}%", SafetyLevel.EMERGENCY, current_time)
                self.emergency_action.emit(uav_id, "EMERGENCY_LAND")
                self.emergency_land_triggered.emit(uav_id, f"Critical battery level: {battery_percent}%")
                
        elif battery_percent <= self.battery_critical_threshold:
            if self._should_send_alert(uav_id, AlertType.CRITICAL_BATTERY, current_time):
                self._send_alert(uav_id, AlertType.CRITICAL_BATTERY, 
                               f"Critical battery: {battery_percent}%", SafetyLevel.CRITICAL, current_time)
                
        elif battery_percent <= self.battery_warning_threshold:
            if self._should_send_alert(uav_id, AlertType.LOW_BATTERY, current_time):
                self._send_alert(uav_id, AlertType.LOW_BATTERY, 
                               f"Low battery: {battery_percent}%", SafetyLevel.WARNING, current_time)

    def _monitor_communication(self, uav_id, uav_state, current_time):
        """Monitor communication status."""
        if uav_state.last_update:
            time_since_update = current_time - uav_state.last_update
            
            if time_since_update > self.communication_timeout:
                if self._should_send_alert(uav_id, AlertType.COMM_LOSS, current_time):
                    self._send_alert(uav_id, AlertType.COMM_LOSS, 
                                   f"Communication lost for {time_since_update:.1f}s", 
                                   SafetyLevel.CRITICAL, current_time)
                    # Trigger emergency RTL after prolonged communication loss
                    if time_since_update > self.communication_timeout * 2:  # Double timeout
                        self.emergency_rtl_triggered.emit(uav_id, f"Communication lost for {time_since_update:.1f}s")
                        self.emergency_action.emit(uav_id, "EMERGENCY_RTL")

    def _monitor_gps(self, uav_id, uav_state, current_time):
        """Monitor GPS status."""
        if uav_state.gps_fix_type < 3:  # Less than 3D fix
            if self._should_send_alert(uav_id, AlertType.GPS_LOSS, current_time):
                self._send_alert(uav_id, AlertType.GPS_LOSS, 
                               f"GPS fix lost (type: {uav_state.gps_fix_type})", 
                               SafetyLevel.CRITICAL, current_time)
        
        if uav_state.satellites_visible < 6:  # Minimum satellites
            if self._should_send_alert(uav_id, AlertType.GPS_LOSS, current_time):
                self._send_alert(uav_id, AlertType.GPS_LOSS, 
                               f"Low satellite count: {uav_state.satellites_visible}", 
                               SafetyLevel.WARNING, current_time)

    def _monitor_altitude(self, uav_id, uav_state, current_time):
        """Monitor altitude limits."""
        altitude_agl = uav_state.height  # AGL height
        
        if altitude_agl > self.max_altitude:
            if self._should_send_alert(uav_id, AlertType.ALTITUDE_VIOLATION, current_time):
                self._send_alert(uav_id, AlertType.ALTITUDE_VIOLATION, 
                               f"Altitude too high: {altitude_agl:.1f}m AGL", 
                               SafetyLevel.CRITICAL, current_time)
                
        elif altitude_agl < self.min_altitude and uav_state.armed:
            if self._should_send_alert(uav_id, AlertType.ALTITUDE_VIOLATION, current_time):
                self._send_alert(uav_id, AlertType.ALTITUDE_VIOLATION, 
                               f"Altitude too low: {altitude_agl:.1f}m AGL", 
                               SafetyLevel.WARNING, current_time)

    def _monitor_speed(self, uav_id, uav_state, current_time):
        """Monitor ground speed limits."""
        if uav_state.ground_speed > self.max_speed:
            if self._should_send_alert(uav_id, AlertType.EXCESSIVE_SPEED, current_time):
                self._send_alert(uav_id, AlertType.EXCESSIVE_SPEED, 
                               f"Excessive speed: {uav_state.ground_speed:.1f} m/s", 
                               SafetyLevel.WARNING, current_time)

    def _monitor_attitude(self, uav_id, uav_state, current_time):
        """Monitor attitude (roll/pitch) limits."""
        roll_deg = math.degrees(abs(uav_state.roll))
        pitch_deg = math.degrees(abs(uav_state.pitch))
        
        if roll_deg > self.max_roll_pitch or pitch_deg > self.max_roll_pitch:
            if self._should_send_alert(uav_id, AlertType.ATTITUDE_EXTREME, current_time):
                self._send_alert(uav_id, AlertType.ATTITUDE_EXTREME, 
                               f"Extreme attitude: roll={roll_deg:.1f}°, pitch={pitch_deg:.1f}°", 
                               SafetyLevel.CRITICAL, current_time)
                # Trigger emergency RTL for extreme attitude
                if roll_deg > self.max_roll_pitch * 1.5 or pitch_deg > self.max_roll_pitch * 1.5:
                    self.emergency_rtl_triggered.emit(uav_id, f"Extreme attitude: roll={roll_deg:.1f}°, pitch={pitch_deg:.1f}°")
                    self.emergency_action.emit(uav_id, "EMERGENCY_RTL")

    def _monitor_mission_timeout(self, uav_id, uav_state, current_time):
        """Monitor mission timeout."""
        if uav_id in self.mission_start_times:
            mission_duration = current_time - self.mission_start_times[uav_id]
            
            if mission_duration > self.mission_timeout:
                if self._should_send_alert(uav_id, AlertType.MISSION_TIMEOUT, current_time):
                    self._send_alert(uav_id, AlertType.MISSION_TIMEOUT, 
                                   f"Mission timeout: {mission_duration/60:.1f} minutes", 
                                   SafetyLevel.WARNING, current_time)

    def _should_send_alert(self, uav_id, alert_type, current_time):
        """Check if alert should be sent (not in cooldown)."""
        last_time = self.last_alert_time[uav_id].get(alert_type, 0)
        return (current_time - last_time) > self.alert_cooldown

    def _send_alert(self, uav_id, alert_type, message, safety_level, current_time):
        """Send safety alert and update tracking."""
        alert_data = {
            'timestamp': current_time,
            'alert_type': alert_type.value,
            'message': message,
            'safety_level': safety_level.value
        }
        
        # Update tracking
        self.alert_history[uav_id].append(alert_data)
        self.last_alert_time[uav_id][alert_type] = current_time
        
        # Emit signals
        self.safety_alert.emit(uav_id, alert_type.value, message)
        
        # Log based on severity
        if safety_level == SafetyLevel.EMERGENCY:
            self.logger.critical(f"EMERGENCY - {uav_id}: {message}")
        elif safety_level == SafetyLevel.CRITICAL:
            self.logger.error(f"CRITICAL - {uav_id}: {message}")
        elif safety_level == SafetyLevel.WARNING:
            self.logger.warning(f"WARNING - {uav_id}: {message}")

    def _update_safety_status(self, uav_id):
        """Update overall safety status for UAV."""
        current_time = time.time()
        recent_alerts = [
            alert for alert in self.alert_history[uav_id] 
            if (current_time - alert['timestamp']) < 60  # Last minute
        ]
        
        # Determine safety level based on recent alerts
        if any(alert['safety_level'] == SafetyLevel.EMERGENCY.value for alert in recent_alerts):
            new_status = SafetyLevel.EMERGENCY
        elif any(alert['safety_level'] == SafetyLevel.CRITICAL.value for alert in recent_alerts):
            new_status = SafetyLevel.CRITICAL
        elif any(alert['safety_level'] == SafetyLevel.WARNING.value for alert in recent_alerts):
            new_status = SafetyLevel.WARNING
        else:
            new_status = SafetyLevel.NORMAL
        
        # Emit signal if status changed
        if self.uav_safety_status[uav_id] != new_status:
            self.uav_safety_status[uav_id] = new_status
            self.safety_status_changed.emit(uav_id, new_status.value)

    def _calculate_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two GPS coordinates in meters."""
        # Haversine formula
        R = 6371000  # Earth radius in meters
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat/2) * math.sin(delta_lat/2) + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(delta_lon/2) * math.sin(delta_lon/2))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c

    def handle_emergency(self, uav_id, emergency_type):
        """Handle emergency situations manually triggered."""
        self.logger.critical(f"Manual emergency triggered for UAV {uav_id}: {emergency_type}")
        self.emergency_action.emit(uav_id, emergency_type)
        
        # Emit specific emergency signals based on type
        if emergency_type in ["EMERGENCY_RTL", "RTL"]:
            self.emergency_rtl_triggered.emit(uav_id, f"Manual emergency RTL: {emergency_type}")
        elif emergency_type in ["EMERGENCY_LAND", "LAND"]:
            self.emergency_land_triggered.emit(uav_id, f"Manual emergency land: {emergency_type}")
        elif emergency_type in ["EMERGENCY_DISARM", "DISARM"]:
            self.emergency_disarm_triggered.emit(uav_id, f"Manual emergency disarm: {emergency_type}")
    
    def trigger_emergency_rtl(self, uav_id, reason):
        """Trigger emergency RTL for a specific UAV."""
        self.emergency_rtl_triggered.emit(uav_id, reason)
        self.emergency_action.emit(uav_id, "EMERGENCY_RTL")
        
    def trigger_emergency_land(self, uav_id, reason):
        """Trigger emergency land for a specific UAV."""
        self.emergency_land_triggered.emit(uav_id, reason)
        self.emergency_action.emit(uav_id, "EMERGENCY_LAND")
        
    def trigger_emergency_disarm(self, uav_id, reason):
        """Trigger emergency disarm for a specific UAV."""
        self.emergency_disarm_triggered.emit(uav_id, reason)
        self.emergency_action.emit(uav_id, "EMERGENCY_DISARM")

    def get_safety_status(self, uav_id):
        """Get current safety status for a UAV."""
        return self.uav_safety_status.get(uav_id, SafetyLevel.NORMAL)

    def get_alert_history(self, uav_id, limit=10):
        """Get recent alert history for a UAV."""
        alerts = self.alert_history.get(uav_id, [])
        return alerts[-limit:] if alerts else []

    def clear_alert_history(self, uav_id):
        """Clear alert history for a UAV."""
        if uav_id in self.alert_history:
            self.alert_history[uav_id].clear()
            self.logger.info(f"Alert history cleared for {uav_id}")

    def get_all_safety_statuses(self):
        """Get safety status for all UAVs."""
        return self.uav_safety_status.copy()