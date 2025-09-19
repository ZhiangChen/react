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

        # Telemetry Connection Status
        self.telem1_status = False  # True if Telem1 is connected (primary connection)
        self.telem2_status = False  # True if Telem2 is connected
        self.last_update = None  # Timestamp of last telemetry update

        # Battery Time
        self.battery_status = battery_status
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

    def is_connected(self):
        """Check if the UAV is currently connected via Telem1 (primary connection)."""
        return self.telem1_status

    def get_telemetry(self):
        return {
            'uav_id': self.uav_id,
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
            'connected': self.telem1_status,  # Primary connection status
            'last_update': self.last_update,
            'remaining_battery_time': self.remaining_battery_time,
            'average_power_consumption': self.average_power_consumption
        }