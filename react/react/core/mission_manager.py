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
    mission_upload_requested = Signal(str, str)  # uav_id, waypoint_file_path
    mission_upload_result = Signal(str, bool, int, str)  # uav_id, success, waypoints, message
    
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

    def load_mission_to_uav(self, uav_id, waypoint_file_path):
        """Load mission waypoints from file to specific UAV.
        
        Args:
            uav_id (str): Target UAV identifier
            waypoint_file_path (str): Path to waypoint file (.waypoints or .mission format)
            
        Returns:
            bool: True if mission request was processed, False otherwise
        """
        if uav_id not in self.uav_states:
            self.logger.warning(f"Cannot load mission to unknown UAV: {uav_id}")
            return False
            
        import os
        if not os.path.exists(waypoint_file_path):
            self.logger.error(f"Waypoint file not found: {waypoint_file_path}")
            return False
            
        try:
            # Generate mission ID from file
            mission_id = f'mission_{os.path.basename(waypoint_file_path)}_{int(time.time())}'
            
            # Initialize mission tracking (will be updated when upload completes)
            self.mission_status[uav_id] = {
                'mission_id': mission_id,
                'mission_file': waypoint_file_path,
                'status': 'loading',  # Status: loading -> uploaded -> active -> completed/failed/aborted
                'start_time': None,
                'current_waypoint': 0,
                'total_waypoints': 0,  # Will be updated after parsing
                'progress_percent': 0.0
            }
            
            # Emit signal to request mission upload (TelemetryManager should handle this)
            self.mission_upload_requested.emit(uav_id, waypoint_file_path)
            
            self.logger.info(f"Mission upload requested for UAV {uav_id}: {waypoint_file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to request mission load for {uav_id}: {e}")
            return False

    def mission_upload_completed(self, uav_id, success, total_waypoints=0):
        """Called when mission upload is completed.
        
        Args:
            uav_id (str): Target UAV identifier
            success (bool): Whether upload was successful
            total_waypoints (int): Total number of waypoints uploaded
        """
        if uav_id not in self.mission_status:
            self.logger.warning(f"No mission loading status found for UAV {uav_id}")
            return
            
        if success:
            self.mission_status[uav_id]['status'] = 'uploaded'
            self.mission_status[uav_id]['total_waypoints'] = total_waypoints
            self.waypoint_progress[uav_id] = 0
            
            # Store mission data for tracking
            self.active_missions[uav_id] = {
                'mission_id': self.mission_status[uav_id]['mission_id'],
                'mission_file': self.mission_status[uav_id]['mission_file'],
                'total_waypoints': total_waypoints
            }
            
            mission_id = self.mission_status[uav_id]['mission_id']
            self.logger.info(f"Mission {mission_id} successfully uploaded to UAV {uav_id} ({total_waypoints} waypoints)")
            # Emit success signal
            self.mission_upload_result.emit(uav_id, True, total_waypoints, f"Successfully uploaded {total_waypoints} waypoints")
        else:
            # Upload failed, clean up
            mission_id = self.mission_status[uav_id]['mission_id']
            del self.mission_status[uav_id]
            self.logger.error(f"Mission upload failed for UAV {uav_id}: {mission_id}")
            # Emit failure signal
            self.mission_upload_result.emit(uav_id, False, 0, "Upload failed")

    def mission_upload_failed(self, uav_id, error_message):
        """Called when mission upload fails.
        
        Args:
            uav_id (str): Target UAV identifier  
            error_message (str): Error description
        """
        self.logger.error(f"Mission upload failed for UAV {uav_id}: {error_message}")
        # Emit failure signal with specific error
        if uav_id in self.mission_status:
            del self.mission_status[uav_id]
        self.mission_upload_result.emit(uav_id, False, 0, error_message)

    def start_mission(self, uav_id):
        """Start AUTO mission on UAV."""
        if uav_id not in self.active_missions:
            self.logger.warning(f"No mission loaded for UAV {uav_id}")
            return False
            
        try:
            mission_data = self.active_missions[uav_id]
            mission_id = self.mission_status[uav_id]['mission_id']
            
            # Reset mission timer for new mission
            uav_state = self.app.uav_states.get(uav_id)
            if uav_state:
                uav_state.reset_mission_timer()
                self.logger.info(f"Mission timer reset for {uav_id}")
            
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