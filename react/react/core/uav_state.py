class UAVState:
    def __init__(self, uav_id, latitude=0.0, longitude=0.0, altitude=0.0, mode='DISARMED', battery_status=100):
        self.uav_id = uav_id
        self.latitude = latitude
        self.longitude = longitude
        self.altitude = altitude  # MSL (Mean Sea Level) altitude in meters
        self.height = 0.0  # AGL (Above Ground Level) height in meters
        self.mode = mode
        self.heading = 0.0
        self.ground_speed = 0.0
        self.vertical_speed = 0.0
        self.roll = 0.0
        self.pitch = 0.0
        self.yaw = 0.0
        self.gps_fix_type = 0
        self.satellites_visible = 0
        self.armed = False
        
        # Home position (set when UAV is armed or first GPS fix)
        self.home_lat = 0.0
        self.home_lng = 0.0
        self.home_alt = 0.0

        # Telemetry Connection Status
        self.telem1_status = False  # True if Telem1 is connected (primary connection)
        self.telem2_status = False  # True if Telem2 is connected
        self.last_update = None  # Timestamp of last telemetry update

        # Battery Time
        self.battery_status = battery_status
        
        # Mission Timer
        self.mission_start_time = None  # Timestamp when mission started (takeoff)
        self.mission_elapsed_time = 0.0  # Elapsed mission time in seconds
        self.mission_running = False  # True if mission timer is running
        
        # Pending command tracking for optimistic updates
        self.pending_arm_command = None  # Timestamp when ARM command was sent
        self.pending_disarm_command = None  # Timestamp when DISARM command was sent
        self.command_timeout = 3.0  # Seconds to wait before allowing telemetry override
        self.remaining_battery_time = 0.0  # Estimated remaining battery time in seconds
        self.average_power_consumption = 1.0  # Example: 1% battery per minute (adjust as needed)

    def update_telemetry(self, latitude=None, longitude=None, altitude=None, height=None, mode=None, battery_status=None, 
                         heading=None, ground_speed=None, vertical_speed=None, roll=None, pitch=None, yaw=None, 
                         gps_fix_type=None, satellites_visible=None, armed=None, telem1_status=None, telem2_status=None):
        """Update telemetry data for the UAV."""
        import time
        
        # Update timestamp
        self.last_update = time.time()
        
        if latitude is not None:
            self.latitude = latitude
        if longitude is not None:
            self.longitude = longitude
        if altitude is not None:
            self.altitude = altitude
        if height is not None:
            self.height = height
        if mode is not None:
            self.mode = mode
        if battery_status is not None:
            self.battery_status = battery_status
            self.update_remaining_battery_time()  # Update remaining battery time when battery status changes
        if heading is not None:
            self.heading = heading
        if ground_speed is not None:
            self.ground_speed = ground_speed
        if vertical_speed is not None:
            self.vertical_speed = vertical_speed
        if roll is not None:
            self.roll = roll
        if pitch is not None:
            self.pitch = pitch
        if yaw is not None:
            self.yaw = yaw
        if gps_fix_type is not None:
            self.gps_fix_type = gps_fix_type
        if satellites_visible is not None:
            self.satellites_visible = satellites_visible
        if armed is not None:
            self.armed = armed
        if telem1_status is not None:
            self.telem1_status = telem1_status
        if telem2_status is not None:
            self.telem2_status = telem2_status
            
        # Update home position if needed (when UAV gets first good GPS fix)
        self.update_home_position_if_needed()

    def update_telemetry_protected(self, **kwargs):
        """Update telemetry but respect pending command states to prevent flickering."""
        import time
        current_time = time.time()
        
        # Check if we have a pending ARM command that should override armed status
        if 'armed' in kwargs:
            if self.pending_arm_command and (current_time - self.pending_arm_command) < self.command_timeout:
                # ARM command is pending, keep optimistic armed=True state
                if not kwargs['armed']:  # Real telemetry says disarmed, but we're pending ARM
                    kwargs['armed'] = True  # Keep optimistic state
            elif self.pending_disarm_command and (current_time - self.pending_disarm_command) < self.command_timeout:
                # DISARM command is pending, keep optimistic armed=False state  
                if kwargs['armed']:  # Real telemetry says armed, but we're pending DISARM
                    kwargs['armed'] = False  # Keep optimistic state
                    
        # If enough time has passed, clear pending commands
        if self.pending_arm_command and (current_time - self.pending_arm_command) >= self.command_timeout:
            self.pending_arm_command = None
        if self.pending_disarm_command and (current_time - self.pending_disarm_command) >= self.command_timeout:
            self.pending_disarm_command = None
            
        # Update telemetry normally
        self.update_telemetry(**kwargs)

    def set_pending_arm_command(self):
        """Set that an ARM command is pending - used for optimistic updates."""
        import time
        self.pending_arm_command = time.time()
        self.pending_disarm_command = None  # Clear any pending disarm
        self.armed = True  # Optimistic update

    def set_pending_disarm_command(self):
        """Set that a DISARM command is pending - used for optimistic updates."""
        import time
        self.pending_disarm_command = time.time()
        self.pending_arm_command = None  # Clear any pending arm
        self.armed = False  # Optimistic update

    def update_remaining_battery_time(self):
        """Estimate the remaining battery time based on the current battery status and power consumption."""
        if self.battery_status > 0 and self.average_power_consumption > 0:
            # Convert average power consumption to seconds (e.g., 1% per minute = 60 seconds per 1%)
            consumption_rate_per_second = self.average_power_consumption / 60.0
            self.remaining_battery_time = (self.battery_status / consumption_rate_per_second)
        else:
            self.remaining_battery_time = 0.0

    def set_connected(self, connected):
        """Set the Telem1 connection status of the UAV (primary connection)."""
        self.telem1_status = connected
        
    def set_home_position(self, latitude=None, longitude=None, altitude=None):
        """Set the home position of the UAV."""
        if latitude is not None:
            self.home_lat = latitude
        if longitude is not None:
            self.home_lng = longitude
        if altitude is not None:
            self.home_alt = altitude
            
    def update_home_position_if_needed(self):
        """Update home position if not set and UAV has valid GPS."""
        if (self.home_lat == 0.0 and self.home_lng == 0.0 and 
            self.gps_fix_type >= 3 and self.latitude != 0.0 and self.longitude != 0.0):
            self.set_home_position(self.latitude, self.longitude, self.altitude)

    def is_connected(self):
        """Check if the UAV is currently connected via Telem1 (primary connection)."""
        return self.telem1_status

    def get_telemetry(self):
        return {
            'uav_id': self.uav_id,
            'position': {
                'latitude': self.latitude,
                'longitude': self.longitude,
                'altitude': self.altitude,
                'height': self.height
            },
            'attitude': {
                'heading': self.heading,
                'roll': self.roll,
                'pitch': self.pitch,
                'yaw': self.yaw
            },
            'motion': {
                'ground_speed': self.ground_speed,
                'vertical_speed': self.vertical_speed
            },
            'flight_status': {
                'mode': self.mode,
                'armed': self.armed,
                'flight_mode': self.mode  # Alias for compatibility
            },
            'battery': {
                'battery_status': self.battery_status,
                'remaining_percent': self.battery_status,  # Alias for compatibility
                'remaining_battery_time': self.remaining_battery_time,
                'average_power_consumption': self.average_power_consumption,
            'mission_elapsed_time': self.get_mission_elapsed_time(),
            'mission_running': self.mission_running
        },
            'connections': {
                'telem1_status': self.telem1_status,
                'telem2_status': self.telem2_status,
                'telem1_connected': self.telem1_status,  # Alias for compatibility
                'telem2_connected': self.telem2_status,  # Alias for compatibility
                'connected': self.telem1_status  # Primary connection status
            },
            'gps': {
                'fix_type': self.gps_fix_type,
                'satellites_visible': self.satellites_visible
            },
            'last_update': self.last_update,
            
            # Keep flat structure for backward compatibility
            'latitude': self.latitude,
            'longitude': self.longitude,
            'altitude': self.altitude,
            'height': self.height,
            'mode': self.mode,
            'battery_status': self.battery_status,
            'heading': self.heading,
            'ground_speed': self.ground_speed,
            'vertical_speed': self.vertical_speed,
            'roll': self.roll,
            'pitch': self.pitch,
            'yaw': self.yaw,
            'gps_fix_type': self.gps_fix_type,
            'satellites_visible': self.satellites_visible,
            'armed': self.armed,
            'telem1_status': self.telem1_status,
            'telem2_status': self.telem2_status,
            'connected': self.telem1_status,
            'remaining_battery_time': self.remaining_battery_time,
            'average_power_consumption': self.average_power_consumption,
            'mission_elapsed_time': self.get_mission_elapsed_time(),
            'mission_running': self.mission_running
        }

    def start_mission_timer(self):
        """Start the mission timer (called on takeoff)"""
        import time
        self.mission_start_time = time.time()
        self.mission_elapsed_time = 0.0
        self.mission_running = True
    
    def stop_mission_timer(self):
        """Stop the mission timer (called on landing)"""
        if self.mission_running and self.mission_start_time:
            import time
            self.mission_elapsed_time = time.time() - self.mission_start_time
        self.mission_running = False
    
    def get_mission_elapsed_time(self):
        """Get the current mission elapsed time in seconds"""
        if not self.mission_running or not self.mission_start_time:
            return self.mission_elapsed_time
        import time
        return time.time() - self.mission_start_time
    
    def reset_mission_timer(self):
        """Reset the mission timer (called when new mission starts)"""
        self.mission_start_time = None
        self.mission_elapsed_time = 0.0
        self.mission_running = False
