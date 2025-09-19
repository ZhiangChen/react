# core/mission_manager.py

import logging
import time
from PySide6.QtCore import QObject, Signal, QTimer

class MissionManager(QObject):
    # Mission execution signals
    mission_started = Signal(str, str)        # uav_id, mission_id
    mission_paused = Signal(str)              # uav_id
    mission_resumed = Signal(str)             # uav_id
    mission_completed = Signal(str, bool)     # uav_id, success
    mission_aborted = Signal(str, str)        # uav_id, reason
    waypoint_reached = Signal(str, int)       # uav_id, waypoint_number
    mission_progress = Signal(str, float)     # uav_id, progress_percent
    
    def __init__(self, uav_states: dict, config: dict):
        super().__init__()
        self.uav_states = uav_states
        self.config = config
        
        # Mission execution tracking
        self.active_missions = {}  # uav_id -> mission_data
        self.mission_status = {}   # uav_id -> status_dict
        self.waypoint_progress = {}  # uav_id -> current_waypoint_index
        
        # Mission monitoring
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self._monitor_missions)
        
        # Get logger using standard Python logging
        self.logger = logging.getLogger("REACT.MissionManager")
        self.logger.info("Mission Manager initialized")

    def start(self):
        """Start mission monitoring."""
        self.monitor_timer.start(1000)  # Check every second
        self.logger.info("Mission monitoring started")

    def stop(self):
        """Stop mission monitoring."""
        self.monitor_timer.stop()
        self.logger.info("Mission monitoring stopped")

    def load_mission_to_uav(self, uav_id, mission_data):
        """Load mission waypoints to specific UAV."""
        if uav_id not in self.uav_states:
            self.logger.warning(f"Cannot load mission to unknown UAV: {uav_id}")
            return False
            
        try:
            mission_id = mission_data.get('mission_id', f'mission_{int(time.time())}')
            
            # Initialize mission tracking
            self.active_missions[uav_id] = mission_data
            self.mission_status[uav_id] = {
                'mission_id': mission_id,
                'status': 'loaded',
                'start_time': None,
                'current_waypoint': 0,
                'total_waypoints': len(mission_data.get('waypoints', [])),
                'progress_percent': 0.0
            }
            self.waypoint_progress[uav_id] = 0
            
            self.logger.info(f"Mission {mission_id} loaded to UAV {uav_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load mission to {uav_id}: {e}")
            return False

    def start_mission(self, uav_id):
        """Start AUTO mission on UAV."""
        if uav_id not in self.active_missions:
            self.logger.warning(f"No mission loaded for UAV {uav_id}")
            return False
            
        try:
            mission_data = self.active_missions[uav_id]
            mission_id = self.mission_status[uav_id]['mission_id']
            
            # Update status
            self.mission_status[uav_id]['status'] = 'active'
            self.mission_status[uav_id]['start_time'] = time.time()
            
            self.mission_started.emit(uav_id, mission_id)
            self.logger.info(f"Mission {mission_id} started for UAV {uav_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start mission for {uav_id}: {e}")
            return False

    def pause_mission(self, uav_id):
        """Pause current mission."""
        if uav_id not in self.active_missions:
            self.logger.warning(f"No active mission for UAV {uav_id}")
            return False
            
        if self.mission_status[uav_id]['status'] == 'active':
            self.mission_status[uav_id]['status'] = 'paused'
            self.mission_paused.emit(uav_id)
            self.logger.info(f"Mission paused for UAV {uav_id}")
            return True
        return False

    def resume_mission(self, uav_id):
        """Resume paused mission."""
        if uav_id not in self.active_missions:
            self.logger.warning(f"No mission loaded for UAV {uav_id}")
            return False
            
        if self.mission_status[uav_id]['status'] == 'paused':
            self.mission_status[uav_id]['status'] = 'active'
            self.mission_resumed.emit(uav_id)
            self.logger.info(f"Mission resumed for UAV {uav_id}")
            return True
        return False

    def abort_mission(self, uav_id, reason="Manual abort"):
        """Abort mission with specified reason."""
        if uav_id not in self.active_missions:
            self.logger.warning(f"No active mission for UAV {uav_id}")
            return False
            
        try:
            mission_id = self.mission_status[uav_id]['mission_id']
            self.mission_status[uav_id]['status'] = 'aborted'
            
            # Clean up mission data
            del self.active_missions[uav_id]
            del self.mission_status[uav_id]
            if uav_id in self.waypoint_progress:
                del self.waypoint_progress[uav_id]
            
            self.mission_aborted.emit(uav_id, reason)
            self.logger.warning(f"Mission {mission_id} aborted for UAV {uav_id}: {reason}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to abort mission for {uav_id}: {e}")
            return False

    def complete_mission(self, uav_id, success=True):
        """Mark mission as completed."""
        if uav_id not in self.active_missions:
            return False
            
        try:
            mission_id = self.mission_status[uav_id]['mission_id']
            self.mission_status[uav_id]['status'] = 'completed' if success else 'failed'
            self.mission_status[uav_id]['progress_percent'] = 100.0 if success else 0.0
            
            self.mission_completed.emit(uav_id, success)
            
            if success:
                self.logger.info(f"Mission {mission_id} completed successfully for UAV {uav_id}")
            else:
                self.logger.error(f"Mission {mission_id} failed for UAV {uav_id}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to complete mission for {uav_id}: {e}")
            return False

    def update_waypoint_progress(self, uav_id, waypoint_number):
        """Update current waypoint progress."""
        if uav_id not in self.active_missions:
            return False
            
        try:
            self.waypoint_progress[uav_id] = waypoint_number
            total_waypoints = self.mission_status[uav_id]['total_waypoints']
            
            if total_waypoints > 0:
                progress = (waypoint_number / total_waypoints) * 100.0
                self.mission_status[uav_id]['current_waypoint'] = waypoint_number
                self.mission_status[uav_id]['progress_percent'] = progress
                
                self.waypoint_reached.emit(uav_id, waypoint_number)
                self.mission_progress.emit(uav_id, progress)
                
                self.logger.debug(f"UAV {uav_id} reached waypoint {waypoint_number}/{total_waypoints} ({progress:.1f}%)")
                
                # Check if mission completed
                if waypoint_number >= total_waypoints:
                    self.complete_mission(uav_id, True)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update waypoint progress for {uav_id}: {e}")
            return False

    def _monitor_missions(self):
        """Monitor active missions for progress and issues."""
        current_time = time.time()
        
        for uav_id, status in list(self.mission_status.items()):
            if status['status'] != 'active':
                continue
                
            # Check mission timeout
            if status['start_time']:
                mission_duration = current_time - status['start_time']
                max_duration = self.config.get('safety', {}).get('mission_timeout', 1800)
                
                if mission_duration > max_duration:
                    self.logger.warning(f"Mission timeout for UAV {uav_id} ({mission_duration/60:.1f} min)")
                    self.abort_mission(uav_id, "Mission timeout")
                    
            # Monitor UAV status for mission-related issues
            if uav_id in self.uav_states:
                uav_state = self.uav_states[uav_id]
                
                # Check if UAV is still connected
                if not uav_state.is_connected():
                    self.logger.error(f"UAV {uav_id} disconnected during mission")
                    self.pause_mission(uav_id)
                
                # Check battery level
                if uav_state.battery_status < 15:  # Critical battery during mission
                    self.logger.critical(f"Critical battery during mission for UAV {uav_id}")
                    self.abort_mission(uav_id, "Critical battery level")

    def get_mission_progress(self, uav_id):
        """Get current mission progress."""
        if uav_id in self.mission_status:
            return self.mission_status[uav_id].copy()
        return None

    def get_active_missions(self):
        """Get all active missions."""
        return {
            uav_id: {
                'mission_data': self.active_missions[uav_id],
                'status': self.mission_status[uav_id]
            }
            for uav_id in self.active_missions.keys()
        }

    def get_mission_status(self, uav_id):
        """Get mission status for specific UAV."""
        return self.mission_status.get(uav_id, {'status': 'none'})

    def clear_completed_missions(self):
        """Clear all completed/failed missions."""
        completed_uavs = []
        
        for uav_id, status in self.mission_status.items():
            if status['status'] in ['completed', 'failed', 'aborted']:
                completed_uavs.append(uav_id)
        
        for uav_id in completed_uavs:
            if uav_id in self.active_missions:
                del self.active_missions[uav_id]
            if uav_id in self.mission_status:
                del self.mission_status[uav_id]
            if uav_id in self.waypoint_progress:
                del self.waypoint_progress[uav_id]
        
        self.logger.info(f"Cleared {len(completed_uavs)} completed missions")

    def emergency_abort_all(self):
        """Emergency abort all active missions."""
        active_uavs = [uav_id for uav_id, status in self.mission_status.items() 
                      if status['status'] == 'active']
        
        for uav_id in active_uavs:
            self.abort_mission(uav_id, "Emergency abort all")
        
        self.logger.critical(f"Emergency abort triggered for {len(active_uavs)} missions")