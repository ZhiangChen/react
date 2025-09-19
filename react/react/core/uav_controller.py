# core/uav_controller.py

import logging
from PySide6.QtCore import QObject, Signal
from pymavlink import mavutil

class UAVController(QObject):
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
        self.logger = logging.getLogger("REACT.UAVController")
        self.logger.info("UAV Controller initialized")
    
    def arm_uav(self, uav_id):
        """Arm a specific UAV."""
        if uav_id not in self.uav_states:
            self.logger.warning(f"Cannot arm unknown UAV: {uav_id}")
            return False
            
        command = {
            'type': 'command_long',
            'command_id': mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            'params': [1, 0, 0, 0, 0, 0, 0],  # param1=1 for arm
            'description': 'ARM'
        }
        
        self.logger.info(f"Requesting arm command for UAV {uav_id}")
        self.command_requested.emit(uav_id, command)
        return True
    
    def disarm_uav(self, uav_id):
        """Disarm a specific UAV."""
        if uav_id not in self.uav_states:
            self.logger.warning(f"Cannot disarm unknown UAV: {uav_id}")
            return False
            
        command = {
            'type': 'command_long',
            'command_id': mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            'params': [0, 0, 0, 0, 0, 0, 0],  # param1=0 for disarm
            'description': 'DISARM'
        }
        
        self.logger.info(f"Requesting disarm command for UAV {uav_id}")
        self.command_requested.emit(uav_id, command)
        return True
    
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