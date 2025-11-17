# core/app.py
from PySide6.QtCore import QObject, Slot, Signal, Property
from core.mavlink_manager import MAVLinkManager
from core.command_interface import CommandInterface
from core.safety_monitor import SafetyMonitor
from core.uav_state import UAVState
from pymavlink import mavutil
import logging

class App(QObject):
    # Signal to notify QML of telemetry updates
    telemetry_changed = Signal(str, 'QVariant')  # uav_id, telemetry_data
    # Signal to notify QML when GCS home position changes
    gcs_home_changed = Signal(float, float, float)  # latitude, longitude, altitude
    # Signal to notify QML of mission upload results
    mission_upload_result = Signal(str, bool, str)  # uav_id, success, message
    # Signal to notify QML of mission upload progress
    mission_upload_progress = Signal(str, str, float)  # uav_id, status_message, progress_percent
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.uav_states = {}  

        # Get logger using standard Python logging
        self.logger = logging.getLogger("REACT.App")
        self.logger.info("REACT Application starting...")

        # Initialize managers in dependency order
        self.mavlink_manager = MAVLinkManager(self.uav_states, self.config)
        self._command_interface = CommandInterface(self.uav_states, self.config)
        self.safety_monitor = SafetyMonitor(self.uav_states, self.config)

        # Set up component connections
        self._setup_connections()

        self.logger.info("All managers initialized successfully")

    # QML Property to expose UAV command interface
    @Property(QObject, constant=True)
    def uav_controller(self):
        """Expose command interface to QML (keeps 'uav_controller' name for QML compatibility)."""
        return self._command_interface

    def _setup_connections(self):
        """Set up signal connections between components."""
        self.logger.info("Setting up component connections...")
        
        # Connect telemetry updates
        self.mavlink_manager.telemetry_updated.connect(self.on_telemetry_updated)
        
        # Connect mission upload progress and completion signals
        self.mavlink_manager.mission_upload_progress.connect(self._handle_upload_progress)
        self.mavlink_manager.mission_upload_completed.connect(self._handle_upload_completed)
        
        # Connect CommandInterface commands to MAVLinkManager
        self._command_interface.command_requested.connect(self._handle_command_request)
        
        # Connect SafetyMonitor emergency signals
        self.safety_monitor.emergency_rtl_triggered.connect(self._handle_emergency_rtl)
        self.safety_monitor.emergency_land_triggered.connect(self._handle_emergency_land)
        self.safety_monitor.emergency_disarm_triggered.connect(self._handle_emergency_disarm)
        
        self.logger.info("Component connections established")

    def start(self):
        """Start all managers and services."""
        self.logger.info("Starting REACT application...")
        
        # Start MAVLink manager first (this will start the background thread)
        self.mavlink_manager.start()
        
        # Start safety monitor
        self.safety_monitor.start()
        
        self.logger.info("All services started successfully!")

    def stop(self):
        """Stop all managers and services."""
        self.logger.info("Stopping REACT application...")
        
        # Stop in reverse order
        self.safety_monitor.stop()
        self.mavlink_manager.stop()
        
        self.logger.info("All services stopped.")

    # Signal handlers for component integration
    
    def _handle_command_request(self, uav_id, command):
        """Handle command requests from CommandInterface."""
        self.logger.debug(f"Processing command request for {uav_id}: {command.get('type', 'unknown')}")
        success = self.mavlink_manager.send_command(uav_id, command)
        
        # For ARM/DISARM commands, emit telemetry update to reflect optimistic GUI updates
        if command.get('command_id') == mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM:
            if uav_id in self.uav_states:
                self.telemetry_changed.emit(uav_id, self.uav_states[uav_id].get_telemetry())
        
        # Emit command result signal back to CommandInterface
        self._command_interface.command_sent.emit(uav_id, command.get('type', 'unknown'))
        
        if not success:
            self.logger.warning(f"Command failed for {uav_id}: {command}")

    def _handle_upload_progress(self, uav_id, status_message, progress_percent):
        """Handle mission upload progress updates from MAVLink manager."""
        self.logger.debug(f"Upload progress for {uav_id}: {status_message} ({progress_percent}%)")
        # Forward to QML
        self.mission_upload_progress.emit(uav_id, status_message, progress_percent)
    
    def _handle_upload_completed(self, uav_id, success, message):
        """Handle mission upload completion from MAVLink manager."""
        self.logger.info(f"[TIMING] Upload completed callback received for {uav_id}: success={success}, message={message}")
        
        # Check if this was skipped due to already in progress
        if "already in progress" in message.lower():
            self.logger.info(f"Upload skipped for {uav_id} - already in progress")
            # Don't emit this as a failure result to QML - just silently skip
            # The ongoing upload will complete normally
            return
        
        # Emit final result to QML
        self.mission_upload_result.emit(uav_id, success, message)
        if success:
            self.logger.info(f"Mission upload completed successfully for {uav_id}")
        else:
            self.logger.error(f"Mission upload failed for {uav_id}: {message}")

    def _handle_emergency_rtl(self, uav_id, reason):
        """Handle emergency RTL from SafetyMonitor."""
        self.logger.critical(f"Emergency RTL triggered for {uav_id}: {reason}")
        
        if uav_id == "ALL":
            # Broadcast RTL to all UAVs
            success = self.mavlink_manager.broadcast_emergency_command("RTL")
        else:
            # Single UAV emergency
            success = self.mavlink_manager.abort_mission_rtl(uav_id)
            
        if not success:
            self.logger.error(f"Emergency RTL command failed for {uav_id}")

    def _handle_emergency_land(self, uav_id, reason):
        """Handle emergency land from SafetyMonitor."""
        self.logger.critical(f"Emergency land triggered for {uav_id}: {reason}")
        
        if uav_id == "ALL":
            # Broadcast LAND to all UAVs
            success = self.mavlink_manager.broadcast_emergency_command("LAND")
        else:
            # Single UAV emergency
            success = self._command_interface.land(uav_id)
            
        if not success:
            self.logger.error(f"Emergency land command failed for {uav_id}")

    def _handle_emergency_disarm(self, uav_id, reason):
        """Handle emergency disarm from SafetyMonitor."""
        self.logger.critical(f"Emergency disarm triggered for {uav_id}: {reason}")
        
        if uav_id == "ALL":
            # Broadcast DISARM to all UAVs
            success = self.mavlink_manager.broadcast_emergency_command("DISARM")
        else:
            # Single UAV emergency
            success = self._command_interface.disarm_uav(uav_id)
            
        if not success:
            self.logger.error(f"Emergency disarm command failed for {uav_id}")

    def on_telemetry_updated(self, uav_id, telemetry_data):
        """Handle telemetry updates and emit signal to QML."""
        self.logger.debug(f"Telemetry update for {uav_id}: {telemetry_data}")
        
        # Forward telemetry to other managers that need it
        # SafetyMonitor will receive updates through shared uav_states
        
        # Emit signal to update QML immediately
        self.telemetry_changed.emit(uav_id, telemetry_data)

    # Public API methods for external control
    
    def get_uav_status(self, uav_id):
        """Get current status of a UAV."""
        if uav_id in self.uav_states:
            return self.uav_states[uav_id].get_telemetry()
        return None

    def get_all_uav_status(self):
        """Get status of all UAVs."""
        return {uav_id: state.get_telemetry() for uav_id, state in self.uav_states.items()}

    def get_mission_status(self, uav_id):
        """Get mission status for a UAV - returns basic mission info from telemetry."""
        if uav_id in self.uav_states:
            return {
                'mission_active': self.uav_states[uav_id].mode in ['AUTO', 'GUIDED'],
                'current_waypoint': self.uav_states[uav_id].current_waypoint,
                'total_waypoints': self.uav_states[uav_id].total_waypoints
            }
        return None

    def _parse_waypoint_indices(self, waypoint_file_path):
        """Parse waypoint indices from a mission file.
        
        Returns list of waypoint indices (e.g., [0, 1, 5, 7, 10] for non-continuous missions).
        """
        try:
            with open(waypoint_file_path, 'r') as f:
                lines = f.readlines()
            
            indices = []
            # Skip header line, parse waypoint indices
            for line in lines[1:]:
                line = line.strip()
                if line:
                    parts = line.split('\t')
                    if len(parts) > 0:
                        try:
                            wp_index = int(parts[0])
                            indices.append(wp_index)
                        except ValueError:
                            continue
            
            return indices
        except Exception as e:
            self.logger.error(f"Failed to parse waypoint indices from {waypoint_file_path}: {e}")
            return []

    @Slot(str, str, result=bool)
    def load_mission(self, uav_id, waypoint_file_path):
        """Load a mission to a UAV."""
        import time
        start_time = time.time()
        self.logger.info(f"[TIMING] User clicked upload mission button for {uav_id} at t=0.000s")
        self.logger.info(f"Processing mission upload request for {uav_id}: {waypoint_file_path}")
        
        # Parse waypoint indices from mission file for tracking
        waypoint_indices = self._parse_waypoint_indices(waypoint_file_path)
        
        if waypoint_indices and uav_id in self.uav_states:
            uav_state = self.uav_states[uav_id]
            # For a fresh mission upload, original and uploaded are the same
            uav_state.original_waypoint_indices = waypoint_indices.copy()
            uav_state.uploaded_waypoint_indices = waypoint_indices.copy()
            uav_state.reached_waypoint_indices = []  # Reset reached list
            self.logger.info(f"Initialized mission tracking: waypoint_indices={waypoint_indices}")
        
        # Emit initial progress: upload starting
        self.mission_upload_progress.emit(uav_id, "Starting upload...", 0.0)
        
        success = self.mavlink_manager.load_mission(uav_id, waypoint_file_path)
        
        elapsed = time.time() - start_time
        if success:
            self.logger.info(f"[TIMING] load_mission() returned True at t={elapsed:.3f}s (thread started, not complete!)")
            self.logger.info(f"Mission upload thread started successfully for {uav_id} (actual upload continues in background)")
            # Emit progress: thread started, uploading in background
            self.mission_upload_progress.emit(uav_id, "Uploading in background...", 10.0)
            self.logger.info(f"[TIMING] Progress signal 'Uploading in background' emitted at t={elapsed:.3f}s")
        else:
            self.logger.error(f"[TIMING] load_mission() returned False at t={elapsed:.3f}s")
            self.logger.info(f"Mission upload not started for {uav_id} (may be already in progress)")
        
        return success

    @Slot(str, str, result=bool)
    def resume_mission(self, uav_id, waypoint_file_path):
        """Resume a mission from the last completed waypoint.
        
        Reads the mission file, removes all waypoints up to and including the last completed waypoint,
        then uploads the remaining waypoints to continue the mission.
        """
        import time
        
        # Validate UAV exists and get its state
        if uav_id not in self.uav_states:
            self.logger.error(f"Cannot resume mission - {uav_id} not found")
            return False
        
        uav_state = self.uav_states[uav_id]
        last_completed = uav_state.get_last_completed_waypoint()
        
        # Check if there's a last completed waypoint to resume from
        if last_completed < 0:
            self.logger.error(f"Cannot resume mission for {uav_id} - no waypoints have been completed yet")
            return False
        
        # Get the original waypoint indices
        if not uav_state.original_waypoint_indices:
            self.logger.error(f"Cannot resume - no original waypoint indices stored for {uav_id}")
            return False
        
        self.logger.info(f"Resuming mission for {uav_id} from waypoint after {last_completed}")
        self.logger.info(f"Original waypoint indices: {uav_state.original_waypoint_indices}")
        self.logger.info(f"Reached waypoint indices: {uav_state.reached_waypoint_indices}")
        self.logger.info(f"Reading mission file: {waypoint_file_path}")
        
        # Read the original mission file
        try:
            with open(waypoint_file_path, 'r') as f:
                lines = f.readlines()
        except Exception as e:
            self.logger.error(f"Failed to read mission file {waypoint_file_path}: {e}")
            return False
        
        # Parse the mission file
        if len(lines) < 2:
            self.logger.error(f"Mission file is too short: {len(lines)} lines")
            return False
        
        # First line is header: "QGC WPL 110" or similar
        header = lines[0].strip()
        
        # Build waypoint dict: {wp_index: wp_line}
        waypoint_dict = {}
        for line in lines[1:]:
            line = line.strip()
            if line:
                parts = line.split('\t')
                if len(parts) > 0:
                    try:
                        wp_index = int(parts[0])
                        waypoint_dict[wp_index] = line
                    except ValueError:
                        continue
        
        self.logger.info(f"Original mission has waypoints: {sorted(waypoint_dict.keys())}")
        
        # CRITICAL: Waypoint 0 is the HOME waypoint and MUST be included in every mission upload
        # Find the position of last_completed in the original waypoint list
        # Include HOME (waypoint 0), the last completed waypoint, and all waypoints after it
        try:
            last_completed_idx = uav_state.original_waypoint_indices.index(last_completed)
            self.logger.info(f"Last completed waypoint {last_completed} is at index {last_completed_idx} in original list")
        except ValueError:
            self.logger.error(f"Last completed waypoint {last_completed} not found in original waypoint indices {uav_state.original_waypoint_indices}")
            return False
        
        # Build remaining waypoints: HOME (0) + last_completed + all after
        remaining_wp_indices = []
        
        # ALWAYS include waypoint 0 (HOME) - required by ArduPilot/MAVLink
        if 0 in uav_state.original_waypoint_indices:
            remaining_wp_indices.append(0)
            self.logger.info(f"Including HOME waypoint (index 0) - required by ArduPilot")
        
        # Get the last completed waypoint AND all waypoints after it (skip if it's 0, already added)
        for i in range(last_completed_idx, len(uav_state.original_waypoint_indices)):
            wp_idx = uav_state.original_waypoint_indices[i]
            if wp_idx != 0:  # Don't duplicate waypoint 0
                remaining_wp_indices.append(wp_idx)
        
        if len(remaining_wp_indices) <= 1:  # Only HOME, no mission waypoints
            self.logger.error(f"No mission waypoints remaining after waypoint {last_completed} - mission already complete")
            return False
        
        self.logger.info(f"Resume mission will include {len(remaining_wp_indices)} waypoints (including HOME): {remaining_wp_indices}")
        self.logger.info(f"First mission waypoint (after HOME): {remaining_wp_indices[1] if len(remaining_wp_indices) > 1 else 'none'} (should equal last completed: {last_completed})")
        
        # Build remaining waypoints list and re-index them sequentially
        remaining_waypoints = []
        self.logger.info(f"Re-indexing waypoints for upload:")
        for new_idx, wp_idx in enumerate(remaining_wp_indices):
            if wp_idx in waypoint_dict:
                wp_line = waypoint_dict[wp_idx]
                # Parse the waypoint line and replace the index with sequential numbering
                parts = wp_line.split('\t')
                if len(parts) > 0:
                    old_idx = parts[0]
                    parts[0] = str(new_idx)  # Re-index: 0, 1, 2, 3...
                    remaining_waypoints.append('\t'.join(parts))
                    self.logger.info(f"  Original WP {old_idx} (waypoint_dict key: {wp_idx}) -> new index {new_idx}")
                else:
                    remaining_waypoints.append(wp_line)
            else:
                self.logger.warning(f"Waypoint {wp_idx} not found in mission file!")
        
        self.logger.info(f"Created {len(remaining_waypoints)} re-indexed waypoints for upload")
        
        # CRITICAL: Update state tracking BEFORE uploading
        # Keep original indices, but update uploaded indices to the trimmed list
        uav_state.uploaded_waypoint_indices = remaining_wp_indices.copy()
        # Keep reached_waypoint_indices as-is (already contains reached waypoints)
        self.logger.info(f"State updated: uploaded_waypoint_indices={uav_state.uploaded_waypoint_indices}")
        
        # Create a temporary mission file with the remaining waypoints
        import tempfile
        import os
        
        temp_fd, temp_path = tempfile.mkstemp(suffix='.waypoints', text=True)
        try:
            with os.fdopen(temp_fd, 'w') as f:
                # Write header
                f.write(header + '\n')
                # Write remaining waypoints
                for i, wp_line in enumerate(remaining_waypoints):
                    f.write(wp_line + '\n')
                    if i < 3:  # Log first 3 waypoints for debugging
                        self.logger.info(f"  Temp file waypoint {i}: {wp_line[:80]}...")  # First 80 chars
            
            self.logger.info(f"Created temporary resume mission file: {temp_path} with {len(remaining_waypoints)} waypoints")
            
            # Upload the trimmed mission using the existing upload flow
            start_time = time.time()
            self.logger.info(f"[TIMING] Resume mission upload started for {uav_id} at t=0.000s")
            
            # Emit initial progress
            self.mission_upload_progress.emit(uav_id, f"Resuming from waypoint {last_completed + 1}...", 0.0)
            
            # Upload the mission
            success = self.mavlink_manager.load_mission(uav_id, temp_path)
            
            elapsed = time.time() - start_time
            if success:
                self.logger.info(f"[TIMING] Resume mission upload thread started at t={elapsed:.3f}s")
                self.mission_upload_progress.emit(uav_id, "Uploading resumed mission...", 10.0)
            else:
                self.logger.error(f"[TIMING] Resume mission upload failed at t={elapsed:.3f}s")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to create/upload resume mission: {e}")
            return False
        finally:
            # Clean up temporary file
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    self.logger.debug(f"Cleaned up temporary resume mission file")
            except Exception as e:
                self.logger.warning(f"Failed to clean up temporary file {temp_path}: {e}")

    @Slot(str, str, int, result=bool)
    def resume_mission_from_waypoint(self, uav_id, waypoint_file_path, resume_from_waypoint):
        """Resume a mission from a specified waypoint.
        
        Similar to resume_mission, but allows user to specify which waypoint to resume from
        instead of automatically using the last completed waypoint.
        
        Args:
            uav_id: UAV identifier
            waypoint_file_path: Path to the original mission file
            resume_from_waypoint: Waypoint index to resume from (must be in original mission)
        """
        import time
        
        # Validate UAV exists and get its state
        if uav_id not in self.uav_states:
            self.logger.error(f"Cannot resume mission - {uav_id} not found")
            return False
        
        uav_state = self.uav_states[uav_id]
        
        # Get the original waypoint indices
        if not uav_state.original_waypoint_indices:
            self.logger.error(f"Cannot resume - no original waypoint indices stored for {uav_id}")
            return False
        
        # Validate that resume_from_waypoint is in the original mission
        if resume_from_waypoint not in uav_state.original_waypoint_indices:
            self.logger.error(f"Cannot resume from waypoint {resume_from_waypoint} - not in original mission {uav_state.original_waypoint_indices}")
            return False
        
        self.logger.info(f"Resuming mission for {uav_id} from user-specified waypoint {resume_from_waypoint}")
        self.logger.info(f"Original waypoint indices: {uav_state.original_waypoint_indices}")
        self.logger.info(f"Reached waypoint indices: {uav_state.reached_waypoint_indices}")
        self.logger.info(f"Reading mission file: {waypoint_file_path}")
        
        # Read the original mission file
        try:
            with open(waypoint_file_path, 'r') as f:
                lines = f.readlines()
        except Exception as e:
            self.logger.error(f"Failed to read mission file {waypoint_file_path}: {e}")
            return False
        
        # Parse the mission file
        if len(lines) < 2:
            self.logger.error(f"Mission file is too short: {len(lines)} lines")
            return False
        
        # First line is header: "QGC WPL 110" or similar
        header = lines[0].strip()
        
        # Build waypoint dict: {wp_index: wp_line}
        waypoint_dict = {}
        for line in lines[1:]:
            line = line.strip()
            if line:
                parts = line.split('\t')
                if len(parts) > 0:
                    try:
                        wp_index = int(parts[0])
                        waypoint_dict[wp_index] = line
                    except ValueError:
                        continue
        
        self.logger.info(f"Original mission has waypoints: {sorted(waypoint_dict.keys())}")
        
        # CRITICAL: Waypoint 0 is the HOME waypoint and MUST be included in every mission upload
        # Find the position of resume_from_waypoint in the original waypoint list
        try:
            resume_from_idx = uav_state.original_waypoint_indices.index(resume_from_waypoint)
            self.logger.info(f"Resume waypoint {resume_from_waypoint} is at index {resume_from_idx} in original list")
        except ValueError:
            self.logger.error(f"Resume waypoint {resume_from_waypoint} not found in original waypoint indices {uav_state.original_waypoint_indices}")
            return False
        
        # Build remaining waypoints: HOME (0) + resume_from_waypoint + all after
        remaining_wp_indices = []
        
        # ALWAYS include waypoint 0 (HOME) - required by ArduPilot/MAVLink
        if 0 in uav_state.original_waypoint_indices:
            remaining_wp_indices.append(0)
            self.logger.info(f"Including HOME waypoint (index 0) - required by ArduPilot")
        
        # Get the resume waypoint AND all waypoints after it (skip if it's 0, already added)
        for i in range(resume_from_idx, len(uav_state.original_waypoint_indices)):
            wp_idx = uav_state.original_waypoint_indices[i]
            if wp_idx != 0:  # Don't duplicate waypoint 0
                remaining_wp_indices.append(wp_idx)
        
        if len(remaining_wp_indices) <= 1:  # Only HOME, no mission waypoints
            self.logger.error(f"No mission waypoints remaining from waypoint {resume_from_waypoint} - mission already complete")
            return False
        
        self.logger.info(f"Resume mission will include {len(remaining_wp_indices)} waypoints (including HOME): {remaining_wp_indices}")
        self.logger.info(f"First mission waypoint (after HOME): {remaining_wp_indices[1] if len(remaining_wp_indices) > 1 else 'none'} (resume from: {resume_from_waypoint})")
        
        # Build remaining waypoints list and re-index them sequentially
        remaining_waypoints = []
        self.logger.info(f"Re-indexing waypoints for upload:")
        for new_idx, wp_idx in enumerate(remaining_wp_indices):
            if wp_idx in waypoint_dict:
                wp_line = waypoint_dict[wp_idx]
                # Parse the waypoint line and replace the index with sequential numbering
                parts = wp_line.split('\t')
                if len(parts) > 0:
                    old_idx = parts[0]
                    parts[0] = str(new_idx)  # Re-index: 0, 1, 2, 3...
                    remaining_waypoints.append('\t'.join(parts))
                    self.logger.info(f"  Original WP {old_idx} (waypoint_dict key: {wp_idx}) -> new index {new_idx}")
                else:
                    remaining_waypoints.append(wp_line)
            else:
                self.logger.warning(f"Waypoint {wp_idx} not found in mission file!")
        
        self.logger.info(f"Created {len(remaining_waypoints)} re-indexed waypoints for upload")
        
        # CRITICAL: Update state tracking BEFORE uploading
        # Keep original indices, but update uploaded indices to the trimmed list
        uav_state.uploaded_waypoint_indices = remaining_wp_indices.copy()
        # Keep reached_waypoint_indices as-is (already contains reached waypoints)
        self.logger.info(f"State updated: uploaded_waypoint_indices={uav_state.uploaded_waypoint_indices}")
        
        # Create a temporary mission file with the remaining waypoints
        import tempfile
        import os
        
        temp_fd, temp_path = tempfile.mkstemp(suffix='.waypoints', text=True)
        try:
            with os.fdopen(temp_fd, 'w') as f:
                # Write header
                f.write(header + '\n')
                # Write remaining waypoints
                for i, wp_line in enumerate(remaining_waypoints):
                    f.write(wp_line + '\n')
                    if i < 3:  # Log first 3 waypoints for debugging
                        self.logger.info(f"  Temp file waypoint {i}: {wp_line[:80]}...")  # First 80 chars
            
            self.logger.info(f"Created temporary resume mission file: {temp_path} with {len(remaining_waypoints)} waypoints")
            
            # Upload the trimmed mission using the existing upload flow
            start_time = time.time()
            self.logger.info(f"[TIMING] Resume mission upload started for {uav_id} at t=0.000s")
            
            # Emit initial progress
            self.mission_upload_progress.emit(uav_id, f"Resuming from waypoint {resume_from_waypoint}...", 0.0)
            
            # Upload the mission
            success = self.mavlink_manager.load_mission(uav_id, temp_path)
            
            elapsed = time.time() - start_time
            if success:
                self.logger.info(f"[TIMING] Resume mission upload thread started at t={elapsed:.3f}s")
                self.mission_upload_progress.emit(uav_id, "Uploading resumed mission...", 10.0)
            else:
                self.logger.error(f"[TIMING] Resume mission upload failed at t={elapsed:.3f}s")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to create/upload resume mission: {e}")
            return False
        finally:
            # Clean up temporary file
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    self.logger.debug(f"Cleaned up temporary resume mission file")
            except Exception as e:
                self.logger.warning(f"Failed to clean up temporary file {temp_path}: {e}")

    @Slot(str)
    def start_mission(self, uav_id):
        """Start mission execution for a UAV."""
        self.logger.info(f"Starting mission for {uav_id}")
        return self.mavlink_manager.start_mission(uav_id)

    def abort_mission(self, uav_id, reason="Manual abort"):
        """Abort mission for a UAV."""
        self.logger.warning(f"Aborting mission for {uav_id}: {reason}")
        return self.mavlink_manager.abort_mission_rtl(uav_id)

    def emergency_stop_all(self):
        """Emergency stop all UAVs."""
        self.logger.critical("Emergency stop all UAVs triggered")
        self.safety_monitor.emergency_abort_all()

    @Slot(str, result='QVariant')
    def get_uav_status(self, uav_id):
        """Get UAV status information for QML frontend."""
        if uav_id in self.uav_states:
            uav_state = self.uav_states[uav_id]
            return uav_state.get_telemetry()  # Use the new organized structure
        return None

    @Slot(result='QVariant')
    def getAllUAVs(self):
        """Get all UAV information for QML frontend."""
        uav_list = []
        for uav_id, uav_state in self.uav_states.items():
            uav_info = uav_state.get_telemetry()  # Use the new organized structure
            uav_list.append(uav_info)
        return uav_list

    @Slot(str, result='QVariant')
    def getHomePosition(self, uav_id):
        """Get home position for a specific UAV."""
        if uav_id in self.uav_states:
            uav_state = self.uav_states[uav_id]
            result = {
                'latitude': uav_state.home_lat,
                'longitude': uav_state.home_lng,
                'altitude': uav_state.home_alt,
                'isValid': uav_state.home_lat != 0.0 or uav_state.home_lng != 0.0
            }
            # Only log at DEBUG level to reduce noise
            self.logger.debug(f"getHomePosition({uav_id}): lat={result['latitude']}, lon={result['longitude']}, valid={result['isValid']}")
            return result
        else:
            self.logger.debug(f"getHomePosition({uav_id}): UAV not found in uav_states")
        return {'latitude': 0.0, 'longitude': 0.0, 'altitude': 0.0, 'isValid': False}
    
    @Slot(result='QVariant')
    def getGCSHomePosition(self):
        """Get global GCS home position (ground control station)."""
        gcs_home = self.config.get('gcs_home_position', {})
        if gcs_home and ('latitude' in gcs_home and 'longitude' in gcs_home):
            return {
                'latitude': gcs_home.get('latitude', 0.0),
                'longitude': gcs_home.get('longitude', 0.0),
                'altitude': gcs_home.get('altitude', 0.0),
                'isValid': True
            }
        # Fall back to default_home_position if GCS home not set
        default_home = self.config.get('default_home_position', {})
        has_default = default_home.get('latitude') is not None and default_home.get('longitude') is not None
        return {
            'latitude': default_home.get('latitude', 0.0),
            'longitude': default_home.get('longitude', 0.0),
            'altitude': default_home.get('altitude', 0.0),
            'isValid': has_default
        }
    
    @Slot(float, float, float)
    def setGCSHomePosition(self, latitude, longitude, altitude=0.0):
        """Set global GCS home position (ground control station)."""
        self.logger.info(f"Setting GCS home position to: {latitude}, {longitude}, {altitude}")
        self.config['gcs_home_position'] = {
            'latitude': latitude,
            'longitude': longitude,
            'altitude': altitude
        }
        # Emit signal to notify QML that GCS home has changed
        self.gcs_home_changed.emit(latitude, longitude, altitude)
        self.logger.info("GCS home position updated and signal emitted")

    @Slot(str, result='QVariant')
    def getWaypoints(self, uav_id):
        """Get mission waypoints for a specific UAV."""
        # Return empty array for now - can be implemented when mission planning is added
        return []

    @Slot(result='QVariant')
    def getGeofences(self):
        """Get all geofences."""
        # Return empty array for now - can be implemented when geofencing is added
        return []

    @Slot(str, result='QVariant')
    def getUAVPosition(self, uav_id):
        """Get UAV position for QML."""
        if uav_id in self.uav_states:
            uav_state = self.uav_states[uav_id]
            return {
                'latitude': uav_state.latitude,
                'longitude': uav_state.longitude,
                'altitude': uav_state.altitude,
                'isValid': uav_state.gps_fix_type >= 2
            }
        return {'latitude': 0.0, 'longitude': 0.0, 'altitude': 0.0, 'isValid': False}

    @Slot(str, result=float)
    def getUAVHeading(self, uav_id):
        """Get UAV heading for QML."""
        if uav_id in self.uav_states:
            return self.uav_states[uav_id].heading
        return 0.0

    @Slot(str, result=str)
    def getUAVMode(self, uav_id):
        """Get UAV mode for QML."""
        if uav_id in self.uav_states:
            return self.uav_states[uav_id].mode
        return "UNKNOWN"

    @Slot(str, result=str)
    def getArmedState(self, uav_id):
        """Get UAV armed state for QML."""
        if uav_id in self.uav_states:
            return "ARMED" if self.uav_states[uav_id].armed else "DISARMED"
        return "DISARMED"

    @Slot(result=int)
    def getMaxUAVs(self):
        """Get maximum number of UAVs from config, reloading config each time for dynamic updates."""
        import yaml
        try:
            with open("config.yaml", "r") as f:
                current_config = yaml.safe_load(f)
            return current_config.get("device_options", {}).get("max_uavs", 1)
        except Exception as e:
            self.logger.warning(f"Failed to reload config for max_uavs: {e}")
            # Fall back to cached config
            return self.config.get("device_options", {}).get("max_uavs", 1)

    @Slot(result='QVariant')
    def get_camera_config(self):
        """Get camera configuration from config.yaml for GSD calculations."""
        try:
            camera_config = self.config.get('safety', {}).get('camera', {})
            config_dict = {
                'hfov': float(camera_config.get('hfov', 73.4)),
                'vfov': float(camera_config.get('vfov', 52.0)),
                'image_width': int(camera_config.get('image_width', 8000)),
                'image_height': int(camera_config.get('image_height', 6000))
            }
            self.logger.info(f"Camera config loaded: {config_dict}")
            return config_dict
        except Exception as e:
            self.logger.error(f"Error loading camera config: {e}")
            # Return default values
            return {
                'hfov': 73.4,
                'vfov': 52.0,
                'image_width': 8000,
                'image_height': 6000
            }


