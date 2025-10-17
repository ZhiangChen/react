import sys

# Read the current file
with open('core/uav_state.py', 'r') as f:
    content = f.read()

# Update to_dict method
content = content.replace(
    "            'average_power_consumption': self.average_power_consumption\n        }",
    "            'average_power_consumption': self.average_power_consumption,\n            'mission_elapsed_time': self.get_mission_elapsed_time(),\n            'mission_running': self.mission_running\n        }"
)

# Add new methods at the end
new_methods = '''
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
'''

content += new_methods

# Write back
with open('core/uav_state.py', 'w') as f:
    f.write(content)

print("Updated uav_state.py successfully!")
