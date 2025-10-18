# core/command_interface.py

import logging
from PySide6.QtCore import QObject, Signal, Slot
from pymavlink import mavutil

class CommandInterface(QObject):
    # Signals for command requests (to be handled by app.py)
    command_requested = Signal(str, dict)  # uav_id, command_dict
    
    # Signals for status updates
    command_sent = Signal(str, str)  # uav_id, command_description
    command_completed = Signal(str, str, bool)  # uav_id, command, success

    def __init__(self, uav_states: dict, config: dict):
        super().__init__()
        self.uav_states = uav_states
        self.config = config
        
        # Get logger using standard Python logging
        self.logger = logging.getLogger("REACT.CommandInterface")
        self.logger.info("Command Interface initialized")
    
    @Slot(str)
    def arm_uav(self, uav_id):
        """Arm a specific UAV."""
        if uav_id not in self.uav_states:
            self.logger.warning(f"Cannot arm unknown UAV: {uav_id}")
            return False
        
        # Optimistic UI update with pending command protection
        self.uav_states[uav_id].set_pending_arm_command()
        # Note: The telemetry manager will emit the signal when HEARTBEAT confirms the status
            
        command = {
            'type': 'command_long',
            'command_id': mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            'params': [1, 0, 0, 0, 0, 0, 0],  # param1=1 for arm
            'description': 'ARM'
        }
        
        self.logger.info(f"Requesting arm command for UAV {uav_id}")
        self.command_requested.emit(uav_id, command)
        return True
    
    @Slot(str)
    def disarm_uav(self, uav_id):
        """Disarm a specific UAV."""
        if uav_id not in self.uav_states:
            self.logger.warning(f"Cannot disarm unknown UAV: {uav_id}")
            return False
        
        # Optimistic UI update with pending command protection
        self.uav_states[uav_id].set_pending_disarm_command()
        # Note: The telemetry manager will emit the signal when HEARTBEAT confirms the status
            
        command = {
            'type': 'command_long',
            'command_id': mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            'params': [0, 0, 0, 0, 0, 0, 0],  # param1=0 for disarm
            'description': 'DISARM'
        }
        
        self.logger.info(f"Requesting disarm command for UAV {uav_id}")
        self.command_requested.emit(uav_id, command)
        return True
    
    @Slot(str, float)
    def request_takeoff(self, uav_id, altitude):
        """Command UAV to takeoff to specified altitude.
        
        Per ArduPilot Copter documentation:
        1. Vehicle must be in GUIDED mode before takeoff
        2. Then send MAV_CMD_NAV_TAKEOFF command
        """
        # Convert altitude to float (handles both int and float from QML)
        altitude = float(altitude)
        
        if uav_id not in self.uav_states:
            self.logger.warning(f"Cannot takeoff unknown UAV: {uav_id}")
            return False
        
        # Step 1: Set GUIDED mode (required for takeoff command)
        self.logger.info(f"Setting GUIDED mode for UAV {uav_id} before takeoff")
        if not self.set_mode(uav_id, 'GUIDED'):
            self.logger.error(f"Failed to set GUIDED mode for {uav_id}")
            return False
        
        # Step 2: Send takeoff command
        command = {
            'type': 'command_long',
            'command_id': mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
            'params': [0, 0, 0, 0, 0, 0, altitude],  # param7 is target altitude in meters
            'description': f'TAKEOFF to {altitude}m'
        }
        
        self.logger.info(f"Requesting takeoff to {altitude}m for UAV {uav_id}")
        self.command_requested.emit(uav_id, command)
        return True
    
    @Slot(str, str, result=bool)
    def set_mode(self, uav_id, mode):
        """Set flight mode for a specific UAV."""
        if uav_id not in self.uav_states:
            self.logger.warning(f"Cannot set mode for unknown UAV: {uav_id}")
            return False
        
        # Essential ArduCopter mode mappings
        mode_mappings = {
            'STABILIZE': 0,
            'ALT_HOLD': 2,
            'AUTO': 3,
            'GUIDED': 4,
            'LOITER': 5,
            'RTL': 6,
            'LAND': 9,
            'BRAKE': 17
        }
        
        mode_number = mode_mappings.get(mode.upper())
        if mode_number is None:
            self.logger.error(f"Unknown flight mode: {mode}")
            return False
            
        command = {
            'type': 'set_mode',
            'mode_number': mode_number,
            'mode_name': mode.upper(),
            'description': f'SET_MODE_{mode.upper()}'
        }
        
        self.logger.info(f"Requesting mode change for UAV {uav_id} to {mode}")
        self.command_requested.emit(uav_id, command)
        return True
    
    def takeoff(self, uav_id, altitude):
        """Command UAV to takeoff to specified altitude."""
        if uav_id not in self.uav_states:
            self.logger.warning(f"Cannot takeoff unknown UAV: {uav_id}")
            return False
            
        command = {
            'type': 'command_long',
            'command_id': mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
            'params': [0, 0, 0, 0, 0, 0, altitude],  # param7=altitude
            'description': f'TAKEOFF_{altitude}'
        }
        
        self.logger.info(f"Requesting takeoff for UAV {uav_id} to {altitude} meters")
        self.command_requested.emit(uav_id, command)
        return True

    @Slot(str, result=bool)
    def land(self, uav_id):
        """Command UAV to land."""
        if uav_id not in self.uav_states:
            self.logger.warning(f"Cannot land unknown UAV: {uav_id}")
            return False
            
        command = {
            'type': 'set_mode',
            'mode_number': 9,  # LAND mode
            'mode_name': 'LAND',
            'description': 'LAND'
        }
        
        self.logger.info(f"Requesting LAND mode for UAV {uav_id}")
        self.command_requested.emit(uav_id, command)
        return True

    @Slot(str, result=bool)
    def return_to_launch(self, uav_id):
        """Command UAV to return to launch position."""
        if uav_id not in self.uav_states:
            self.logger.warning(f"Cannot RTL unknown UAV: {uav_id}")
            return False
            
        command = {
            'type': 'set_mode',
            'mode_number': 6,  # RTL mode
            'mode_name': 'RTL',
            'description': 'RTL'
        }
        
        self.logger.info(f"Requesting RTL mode for UAV {uav_id}")
        self.command_requested.emit(uav_id, command)
        return True

    @Slot(str, result=bool)
    def brake(self, uav_id):
        """Command UAV to enter BRAKE mode - immediate stop and hold position."""
        if uav_id not in self.uav_states:
            self.logger.warning(f"Cannot brake unknown UAV: {uav_id}")
            return False
            
        command = {
            'type': 'set_mode',
            'mode_number': 17,  # BRAKE mode
            'mode_name': 'BRAKE',
            'description': 'BRAKE'
        }
        
        self.logger.info(f"Requesting BRAKE mode for UAV {uav_id}")
        self.command_requested.emit(uav_id, command)
        return True

    @Slot(str, result=bool)
    def start_mission(self, uav_id):
        """Start mission for UAV - sets AUTO mode then sends mission start command."""
        if uav_id not in self.uav_states:
            self.logger.warning(f"Cannot start mission for unknown UAV: {uav_id}")
            return False
        
        # Step 1: Set AUTO mode (required for mission execution)
        self.logger.info(f"Setting AUTO mode for UAV {uav_id} before starting mission")
        if not self.set_mode(uav_id, 'AUTO'):
            self.logger.error(f"Failed to set AUTO mode for {uav_id}")
            return False
        
        # Step 2: Send MAV_CMD_MISSION_START command
        command = {
            'type': 'command_long',
            'command_id': mavutil.mavlink.MAV_CMD_MISSION_START,
            'params': [0, 0, 0, 0, 0, 0, 0],  # All params 0 for mission start
            'description': 'MISSION_START'
        }
        
        self.logger.info(f"Requesting MISSION_START for UAV {uav_id}")
        self.command_requested.emit(uav_id, command)
        return True

    def goto_position(self, uav_id, lat, lon, alt):
        """Command UAV to go to specific position."""
        if uav_id not in self.uav_states:
            self.logger.warning(f"Cannot send goto command to unknown UAV: {uav_id}")
            return False
            
        # First set GUIDED mode, then send goto command
        guided_command = {
            'type': 'set_mode',
            'mode_number': 4,  # GUIDED mode
            'mode_name': 'GUIDED',
            'description': 'SET_MODE_GUIDED'
        }
        
        goto_command = {
            'type': 'command_long',
            'command_id': mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
            'params': [0, 0, 0, 0, lat, lon, alt],
            'description': f'GOTO_{lat}_{lon}_{alt}'
        }
        
        self.logger.info(f"Requesting GUIDED mode and goto position for UAV {uav_id}")
        self.command_requested.emit(uav_id, guided_command)
        # Note: In app.py you might want to sequence these commands with a delay
        self.command_requested.emit(uav_id, goto_command)
        return True
    
    def emergency_rtl_all(self):
        """Emergency stop for all UAVs - broadcast RTL command."""
        self.logger.critical("EMERGENCY STOP - Requesting RTL for all UAVs")
        
        emergency_command = {
            'type': 'emergency_broadcast',
            'command_type': 'RTL',
            'description': 'EMERGENCY_RTL_ALL'
        }
        
        # Send to all known UAVs
        for uav_id in self.uav_states.keys():
            self.command_requested.emit(uav_id, emergency_command)
        
        return True
    
    def emergency_land_all(self):
        """Emergency land for all UAVs - broadcast LAND command."""
        self.logger.critical("EMERGENCY LAND - Requesting LAND for all UAVs")
        
        emergency_command = {
            'type': 'emergency_broadcast',
            'command_type': 'LAND',
            'description': 'EMERGENCY_LAND_ALL'
        }
        
        # Send to all known UAVs
        for uav_id in self.uav_states.keys():
            self.command_requested.emit(uav_id, emergency_command)
        
        return True
    
    def emergency_disarm_all(self):
        """Emergency disarm for all UAVs - broadcast DISARM command."""
        self.logger.critical("EMERGENCY DISARM - Requesting DISARM for all UAVs")
        
        emergency_command = {
            'type': 'emergency_broadcast',
            'command_type': 'DISARM',
            'description': 'EMERGENCY_DISARM_ALL'
        }
        
        # Send to all known UAVs
        for uav_id in self.uav_states.keys():
            self.command_requested.emit(uav_id, emergency_command)
        
        return True
    
    def emergency_brake_all(self):
        """Emergency brake for all UAVs - broadcast BRAKE command for immediate stop."""
        self.logger.critical("EMERGENCY BRAKE - Requesting BRAKE for all UAVs")
        
        emergency_command = {
            'type': 'emergency_broadcast',
            'command_type': 'BRAKE',
            'description': 'EMERGENCY_BRAKE_ALL'
        }
        
        # Send to all known UAVs
        for uav_id in self.uav_states.keys():
            self.command_requested.emit(uav_id, emergency_command)
        
        return True
    
    def on_command_result(self, uav_id, command_description, success):
        """Handle command execution results from telemetry manager."""
        if success:
            self.logger.info(f"Command completed successfully: {uav_id} - {command_description}")
            self.command_sent.emit(uav_id, command_description)
        else:
            self.logger.error(f"Command failed: {uav_id} - {command_description}")
        
        self.command_completed.emit(uav_id, command_description, success)