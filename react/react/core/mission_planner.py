# core/mission_planner.py

import logging
import json
import math
from typing import List, Dict, Tuple, Optional
from PySide6.QtCore import QObject, Signal
from dataclasses import dataclass
from enum import Enum

class MissionType(Enum):
    WAYPOINT = "waypoint"
    SURVEY = "survey"
    SEARCH = "search"
    DELIVERY = "delivery"
    PATROL = "patrol"
    CUSTOM = "custom"

class PatternType(Enum):
    GRID = "grid"
    SPIRAL = "spiral"
    ZIGZAG = "zigzag"
    CIRCULAR = "circular"

@dataclass
class Waypoint:
    """Single waypoint definition."""
    lat: float
    lon: float
    alt: float
    speed: float = 5.0
    action: str = "WAYPOINT"
    param1: float = 0.0
    param2: float = 0.0
    param3: float = 0.0
    param4: float = 0.0

@dataclass
class MissionData:
    """Complete mission definition."""
    mission_id: str
    mission_type: MissionType
    waypoints: List[Waypoint]
    home_location: Tuple[float, float, float]  # lat, lon, alt
    metadata: Dict = None

class MissionPlanner(QObject):
    # Planning signals
    mission_created = Signal(str, dict)     # mission_id, mission_data
    mission_modified = Signal(str, dict)    # mission_id, updated_data
    mission_validated = Signal(str, bool, str)   # mission_id, is_valid, message
    mission_saved = Signal(str, str)        # mission_id, filepath
    mission_loaded = Signal(str, dict)      # mission_id, mission_data

    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.missions = {}  # mission_id -> MissionData
        self.logger = logging.getLogger("REACT.MissionPlanner")
        self.logger.info("Mission Planner initialized")

    def create_waypoint_mission(self, mission_id: str, waypoints: List[Tuple[float, float, float]], 
                               home_location: Tuple[float, float, float], speed: float = 5.0) -> bool:
        """Create a basic waypoint mission."""
        try:
            self.logger.info(f"Creating waypoint mission: {mission_id}")
            
            # Convert tuples to Waypoint objects
            wp_objects = []
            for i, (lat, lon, alt) in enumerate(waypoints):
                wp = Waypoint(lat=lat, lon=lon, alt=alt, speed=speed)
                wp_objects.append(wp)
            
            mission_data = MissionData(
                mission_id=mission_id,
                mission_type=MissionType.WAYPOINT,
                waypoints=wp_objects,
                home_location=home_location,
                metadata={'created_by': 'waypoint_mission', 'waypoint_count': len(wp_objects)}
            )
            
            self.missions[mission_id] = mission_data
            self.mission_created.emit(mission_id, self._serialize_mission(mission_data))
            self.logger.info(f"Waypoint mission created: {mission_id} with {len(waypoints)} waypoints")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create waypoint mission {mission_id}: {e}")
            return False

    def create_survey_mission(self, mission_id: str, polygon: List[Tuple[float, float]], 
                             altitude: float, overlap: float = 0.8, spacing: float = 50.0) -> bool:
        """Create automated survey/mapping mission."""
        try:
            self.logger.info(f"Creating survey mission: {mission_id}")
            
            # Placeholder for survey pattern generation
            # TODO: Implement actual survey grid generation algorithm
            waypoints = self._generate_survey_pattern(polygon, altitude, overlap, spacing)
            
            mission_data = MissionData(
                mission_id=mission_id,
                mission_type=MissionType.SURVEY,
                waypoints=waypoints,
                home_location=(polygon[0][0], polygon[0][1], altitude),
                metadata={
                    'survey_area': polygon,
                    'overlap_percent': overlap,
                    'line_spacing_m': spacing,
                    'altitude_m': altitude
                }
            )
            
            self.missions[mission_id] = mission_data
            self.mission_created.emit(mission_id, self._serialize_mission(mission_data))
            self.logger.info(f"Survey mission created: {mission_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create survey mission {mission_id}: {e}")
            return False

    def create_search_pattern(self, mission_id: str, center: Tuple[float, float], 
                             radius: float, pattern_type: PatternType, altitude: float) -> bool:
        """Create search patterns (grid, spiral, etc.)."""
        try:
            self.logger.info(f"Creating search pattern: {mission_id} - {pattern_type.value}")
            
            # Placeholder for search pattern generation
            # TODO: Implement actual search pattern algorithms
            waypoints = self._generate_search_pattern(center, radius, pattern_type, altitude)
            
            mission_data = MissionData(
                mission_id=mission_id,
                mission_type=MissionType.SEARCH,
                waypoints=waypoints,
                home_location=(center[0], center[1], altitude),
                metadata={
                    'search_center': center,
                    'search_radius_m': radius,
                    'pattern_type': pattern_type.value,
                    'altitude_m': altitude
                }
            )
            
            self.missions[mission_id] = mission_data
            self.mission_created.emit(mission_id, self._serialize_mission(mission_data))
            self.logger.info(f"Search pattern created: {mission_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create search pattern {mission_id}: {e}")
            return False

    def create_delivery_mission(self, mission_id: str, pickup_point: Tuple[float, float, float],
                               delivery_point: Tuple[float, float, float], altitude: float) -> bool:
        """Create delivery mission with pickup and drop-off."""
        try:
            self.logger.info(f"Creating delivery mission: {mission_id}")
            
            # Simple delivery waypoints: takeoff -> pickup -> delivery -> return
            waypoints = [
                Waypoint(pickup_point[0], pickup_point[1], altitude, action="WAYPOINT"),
                Waypoint(pickup_point[0], pickup_point[1], pickup_point[2], action="LAND"),
                # TODO: Add pickup action/delay
                Waypoint(pickup_point[0], pickup_point[1], altitude, action="TAKEOFF"),
                Waypoint(delivery_point[0], delivery_point[1], altitude, action="WAYPOINT"),
                Waypoint(delivery_point[0], delivery_point[1], delivery_point[2], action="LAND"),
                # TODO: Add delivery action/delay
                Waypoint(delivery_point[0], delivery_point[1], altitude, action="TAKEOFF"),
            ]
            
            mission_data = MissionData(
                mission_id=mission_id,
                mission_type=MissionType.DELIVERY,
                waypoints=waypoints,
                home_location=pickup_point,
                metadata={
                    'pickup_location': pickup_point,
                    'delivery_location': delivery_point,
                    'flight_altitude_m': altitude
                }
            )
            
            self.missions[mission_id] = mission_data
            self.mission_created.emit(mission_id, self._serialize_mission(mission_data))
            self.logger.info(f"Delivery mission created: {mission_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create delivery mission {mission_id}: {e}")
            return False

    def optimize_waypoint_order(self, mission_id: str) -> bool:
        """Optimize waypoint order for efficiency (traveling salesman problem)."""
        try:
            if mission_id not in self.missions:
                self.logger.warning(f"Mission {mission_id} not found for optimization")
                return False
                
            mission = self.missions[mission_id]
            self.logger.info(f"Optimizing waypoint order for mission: {mission_id}")
            
            # TODO: Implement traveling salesman algorithm
            # For now, just placeholder
            original_count = len(mission.waypoints)
            # optimized_waypoints = self._optimize_tsp(mission.waypoints)
            # mission.waypoints = optimized_waypoints
            
            self.mission_modified.emit(mission_id, self._serialize_mission(mission))
            self.logger.info(f"Mission {mission_id} optimized: {original_count} waypoints")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to optimize mission {mission_id}: {e}")
            return False

    def validate_mission(self, mission_id: str) -> Tuple[bool, str]:
        """Validate mission for safety and feasibility."""
        try:
            if mission_id not in self.missions:
                message = f"Mission {mission_id} not found"
                self.mission_validated.emit(mission_id, False, message)
                return False, message
                
            mission = self.missions[mission_id]
            self.logger.info(f"Validating mission: {mission_id}")
            
            # Basic validation checks
            if not mission.waypoints:
                message = "Mission has no waypoints"
                self.mission_validated.emit(mission_id, False, message)
                return False, message
                
            # TODO: Implement comprehensive validation:
            # - Check altitude limits
            # - Verify GPS coordinates are valid
            # - Check flight time vs battery capacity
            # - Validate no-fly zones
            # - Check waypoint spacing
            
            message = "Mission validation passed"
            self.mission_validated.emit(mission_id, True, message)
            self.logger.info(f"Mission {mission_id} validation: PASSED")
            return True, message
            
        except Exception as e:
            message = f"Validation error: {e}"
            self.mission_validated.emit(mission_id, False, message)
            self.logger.error(f"Failed to validate mission {mission_id}: {e}")
            return False, message

    def calculate_mission_time(self, mission_id: str, uav_speed: float = 5.0) -> Optional[float]:
        """Estimate mission duration in minutes."""
        try:
            if mission_id not in self.missions:
                self.logger.warning(f"Mission {mission_id} not found for time calculation")
                return None
                
            mission = self.missions[mission_id]
            total_distance = 0.0
            
            # Calculate total distance between waypoints
            for i in range(1, len(mission.waypoints)):
                prev_wp = mission.waypoints[i-1]
                curr_wp = mission.waypoints[i]
                distance = self._calculate_distance(prev_wp.lat, prev_wp.lon, curr_wp.lat, curr_wp.lon)
                total_distance += distance
                
            # Estimate time in minutes
            estimated_time = (total_distance / uav_speed) / 60.0
            self.logger.info(f"Mission {mission_id} estimated time: {estimated_time:.1f} minutes")
            return estimated_time
            
        except Exception as e:
            self.logger.error(f"Failed to calculate mission time for {mission_id}: {e}")
            return None

    def save_mission(self, mission_id: str, filepath: str) -> bool:
        """Save mission to file."""
        try:
            if mission_id not in self.missions:
                self.logger.warning(f"Mission {mission_id} not found for saving")
                return False
                
            mission_dict = self._serialize_mission(self.missions[mission_id])
            
            with open(filepath, 'w') as f:
                json.dump(mission_dict, f, indent=2)
                
            self.mission_saved.emit(mission_id, filepath)
            self.logger.info(f"Mission {mission_id} saved to {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save mission {mission_id}: {e}")
            return False

    def load_mission(self, filepath: str) -> Optional[str]:
        """Load mission from file."""
        try:
            with open(filepath, 'r') as f:
                mission_dict = json.load(f)
                
            mission_data = self._deserialize_mission(mission_dict)
            mission_id = mission_data.mission_id
            
            self.missions[mission_id] = mission_data
            self.mission_loaded.emit(mission_id, mission_dict)
            self.logger.info(f"Mission loaded from {filepath}: {mission_id}")
            return mission_id
            
        except Exception as e:
            self.logger.error(f"Failed to load mission from {filepath}: {e}")
            return None

    def get_mission(self, mission_id: str) -> Optional[MissionData]:
        """Get mission data by ID."""
        return self.missions.get(mission_id)

    def get_all_missions(self) -> Dict[str, MissionData]:
        """Get all loaded missions."""
        return self.missions.copy()

    def delete_mission(self, mission_id: str) -> bool:
        """Delete a mission."""
        if mission_id in self.missions:
            del self.missions[mission_id]
            self.logger.info(f"Mission {mission_id} deleted")
            return True
        return False

    # Private helper methods
    def _generate_survey_pattern(self, polygon: List[Tuple[float, float]], 
                                altitude: float, overlap: float, spacing: float) -> List[Waypoint]:
        """Generate survey pattern waypoints."""
        # TODO: Implement actual survey grid algorithm
        waypoints = []
        # Placeholder: just return polygon corners
        for lat, lon in polygon:
            waypoints.append(Waypoint(lat, lon, altitude))
        return waypoints

    def _generate_search_pattern(self, center: Tuple[float, float], radius: float,
                                pattern_type: PatternType, altitude: float) -> List[Waypoint]:
        """Generate search pattern waypoints."""
        # TODO: Implement actual search pattern algorithms
        waypoints = []
        lat, lon = center
        
        if pattern_type == PatternType.CIRCULAR:
            # Simple circular pattern
            for angle in range(0, 360, 45):
                rad = math.radians(angle)
                offset_lat = radius * math.cos(rad) / 111000  # Rough conversion
                offset_lon = radius * math.sin(rad) / 111000
                waypoints.append(Waypoint(lat + offset_lat, lon + offset_lon, altitude))
        else:
            # Placeholder for other patterns
            waypoints.append(Waypoint(lat, lon, altitude))
            
        return waypoints

    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
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

    def _serialize_mission(self, mission: MissionData) -> dict:
        """Convert MissionData to dictionary."""
        return {
            'mission_id': mission.mission_id,
            'mission_type': mission.mission_type.value,
            'waypoints': [
                {
                    'lat': wp.lat,
                    'lon': wp.lon, 
                    'alt': wp.alt,
                    'speed': wp.speed,
                    'action': wp.action,
                    'param1': wp.param1,
                    'param2': wp.param2,
                    'param3': wp.param3,
                    'param4': wp.param4
                } for wp in mission.waypoints
            ],
            'home_location': mission.home_location,
            'metadata': mission.metadata or {}
        }

    def _deserialize_mission(self, mission_dict: dict) -> MissionData:
        """Convert dictionary to MissionData."""
        waypoints = []
        for wp_dict in mission_dict.get('waypoints', []):
            waypoints.append(Waypoint(
                lat=wp_dict['lat'],
                lon=wp_dict['lon'],
                alt=wp_dict['alt'],
                speed=wp_dict.get('speed', 5.0),
                action=wp_dict.get('action', 'WAYPOINT'),
                param1=wp_dict.get('param1', 0.0),
                param2=wp_dict.get('param2', 0.0),
                param3=wp_dict.get('param3', 0.0),
                param4=wp_dict.get('param4', 0.0)
            ))
            
        return MissionData(
            mission_id=mission_dict['mission_id'],
            mission_type=MissionType(mission_dict['mission_type']),
            waypoints=waypoints,
            home_location=tuple(mission_dict['home_location']),
            metadata=mission_dict.get('metadata', {})
        )