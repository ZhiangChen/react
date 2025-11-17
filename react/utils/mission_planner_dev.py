#!/usr/bin/env python3
"""
Mission Planner Development Tool - Survey Grid Generator

README:
-------
This script replicates Mission Planner's "Survey (Grid)" tool for photogrammetry missions.

Requirements:
    pip install matplotlib numpy

Usage:
    python mission_planner_dev.py

Instructions:
    1. Left-click to add polygon vertices
    2. Press 'Enter' or right-click to close the polygon
    3. Enter reference coordinates when prompted
    4. Flight path will be generated and displayed
    5. Waypoints will be saved to a .waypoints file

Configuration:
    Edit the MISSION_PARAMS dictionary below to change flight parameters
"""

import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.collections import LineCollection
import numpy as np
import math
from datetime import datetime
import sys

# ============================================================================
# MISSION PARAMETERS - EDIT THESE VALUES
# ============================================================================
MISSION_PARAMS = {
    'altitude': 50,              # Flight altitude in meters AGL
    'forward_overlap': 70,       # Forward (front) overlap in %
    'lateral_overlap': 70,       # Lateral (side) overlap in %
    'camera_hfov': 73.4,         # Horizontal field of view in degrees
    'camera_vfov': 52.0,         # Vertical field of view in degrees
    'camera_width': 6000,        # Image width in pixels
    'camera_height': 4000,       # Image height in pixels
    'aircraft_speed': 10,        # Speed in m/s
    'grid_angle': None,          # Grid angle in degrees (None = auto-detect longest edge)
}

# ============================================================================
# GLOBAL STATE
# ============================================================================
polygon_points = []
polygon_closed = False
waypoints = []

# Fixed reference point at map origin (can be edited here)
reference_lat = 34.163808   # Default latitude (from config.yaml)
reference_lon = -118.074877  # Default longitude (from config.yaml)

fig = None
ax = None
polygon_patch = None
line = None


# ============================================================================
# COORDINATE CONVERSION FUNCTIONS
# ============================================================================
def latlon_to_meters(lat, lon, ref_lat, ref_lon):
    """
    Convert lat/lon to meters from reference point using flat-earth approximation.
    Suitable for small areas (< 100km).
    
    Returns: (x_meters, y_meters) where x=East, y=North
    """
    # Earth radius in meters
    R = 6371000.0
    
    # Convert to radians
    lat_rad = math.radians(lat)
    ref_lat_rad = math.radians(ref_lat)
    
    # Calculate meters
    x = R * math.radians(lon - ref_lon) * math.cos(ref_lat_rad)
    y = R * math.radians(lat - ref_lat)
    
    return x, y


def meters_to_latlon(x, y, ref_lat, ref_lon):
    """
    Convert meters (from reference point) to lat/lon using flat-earth approximation.
    
    Args:
        x: East displacement in meters
        y: North displacement in meters
        ref_lat, ref_lon: Reference latitude/longitude
        
    Returns: (latitude, longitude)
    """
    # Earth radius in meters
    R = 6371000.0
    
    # Convert reference to radians
    ref_lat_rad = math.radians(ref_lat)
    
    # Calculate lat/lon
    lat = ref_lat + math.degrees(y / R)
    lon = ref_lon + math.degrees(x / (R * math.cos(ref_lat_rad)))
    
    return lat, lon


def pixels_to_meters(px, py, canvas_points, ref_lat, ref_lon):
    """
    Convert canvas pixel coordinates to real-world meters.
    Uses the first polygon point as the reference.
    """
    # Get canvas bounds
    canvas_array = np.array(canvas_points)
    min_x, min_y = canvas_array.min(axis=0)
    max_x, max_y = canvas_array.max(axis=0)
    
    # Assume canvas represents approximately 1km x 1km area (adjustable)
    # This is arbitrary - user should provide scale or click to set reference
    canvas_width_m = 1000
    canvas_height_m = 1000
    
    # Scale pixels to meters
    x_m = (px - min_x) / (max_x - min_x) * canvas_width_m
    y_m = (py - min_y) / (max_y - min_y) * canvas_height_m
    
    return x_m, y_m


# ============================================================================
# CAMERA & GSD CALCULATIONS
# ============================================================================
def calculate_ground_footprint(altitude, hfov, vfov):
    """
    Calculate camera ground footprint at given altitude.
    
    Returns: (width_meters, height_meters)
    """
    hfov_rad = math.radians(hfov)
    vfov_rad = math.radians(vfov)
    
    width = 2 * altitude * math.tan(hfov_rad / 2)
    height = 2 * altitude * math.tan(vfov_rad / 2)
    
    return width, height


def calculate_gsd(altitude, hfov, image_width):
    """
    Calculate Ground Sampling Distance (GSD) in cm/pixel.
    """
    footprint_width = 2 * altitude * math.tan(math.radians(hfov) / 2)
    gsd_m = footprint_width / image_width
    gsd_cm = gsd_m * 100
    return gsd_cm


def calculate_line_spacing(altitude, hfov, lateral_overlap):
    """
    Calculate spacing between parallel survey lines.
    
    spacing = image_footprint_width × (1 - lateral_overlap/100)
    """
    footprint_width, _ = calculate_ground_footprint(altitude, hfov, MISSION_PARAMS['camera_vfov'])
    spacing = footprint_width * (1.0 - lateral_overlap / 100.0)
    return spacing


def calculate_photo_distance(altitude, vfov, forward_overlap):
    """
    Calculate distance between photo captures.
    
    distance = image_footprint_height × (1 - forward_overlap/100)
    """
    _, footprint_height = calculate_ground_footprint(altitude, MISSION_PARAMS['camera_hfov'], vfov)
    distance = footprint_height * (1.0 - forward_overlap / 100.0)
    return distance


# ============================================================================
# POLYGON GEOMETRY FUNCTIONS
# ============================================================================
def point_in_polygon(point, polygon):
    """
    Check if point is inside polygon using ray casting algorithm.
    
    Args:
        point: (x, y) tuple
        polygon: list of (x, y) tuples
        
    Returns: True if inside, False otherwise
    """
    x, y = point
    n = len(polygon)
    inside = False
    
    p1x, p1y = polygon[0]
    for i in range(n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    
    return inside


def line_segment_intersection(p1, p2, p3, p4):
    """
    Find intersection point of two line segments.
    
    Args:
        p1, p2: endpoints of first segment
        p3, p4: endpoints of second segment
        
    Returns: (x, y) intersection point or None
    """
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4
    
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-10:
        return None  # Parallel lines
    
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom
    
    if 0 <= t <= 1 and 0 <= u <= 1:
        x = x1 + t * (x2 - x1)
        y = y1 + t * (y2 - y1)
        return (x, y)
    
    return None


def clip_line_to_polygon(line_start, line_end, polygon):
    """
    Clip a line segment to polygon boundaries.
    
    Returns: list of (x, y) points where line intersects polygon
    """
    intersections = []
    
    # Check all polygon edges for intersections
    n = len(polygon)
    for i in range(n):
        p1 = polygon[i]
        p2 = polygon[(i + 1) % n]
        
        intersection = line_segment_intersection(line_start, line_end, p1, p2)
        if intersection:
            intersections.append(intersection)
    
    # Also check if endpoints are inside polygon
    if point_in_polygon(line_start, polygon):
        intersections.insert(0, line_start)
    if point_in_polygon(line_end, polygon):
        intersections.append(line_end)
    
    # Remove duplicates and sort by distance from line_start
    if intersections:
        intersections = list(set(intersections))
        intersections.sort(key=lambda p: (p[0] - line_start[0])**2 + (p[1] - line_start[1])**2)
    
    return intersections


def get_polygon_bounds(polygon):
    """Get bounding box of polygon."""
    poly_array = np.array(polygon)
    min_x, min_y = poly_array.min(axis=0)
    max_x, max_y = poly_array.max(axis=0)
    return min_x, max_x, min_y, max_y


def get_longest_edge_angle(polygon):
    """
    Find the angle of the longest edge of the polygon.
    This will be used as the grid orientation.
    
    Returns: angle in degrees (0-180)
    """
    max_length = 0
    best_angle = 0
    
    n = len(polygon)
    for i in range(n):
        p1 = polygon[i]
        p2 = polygon[(i + 1) % n]
        
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        length = math.sqrt(dx**2 + dy**2)
        
        if length > max_length:
            max_length = length
            # Calculate angle (0-180 degrees)
            angle = math.degrees(math.atan2(dy, dx))
            # Normalize to 0-180
            if angle < 0:
                angle += 180
            best_angle = angle
    
    return best_angle


# ============================================================================
# SURVEY GRID GENERATION (Mission Planner Algorithm)
# ============================================================================
def generate_survey_grid(polygon_m, altitude, hfov, vfov, lateral_overlap, grid_angle=None):
    """
    Generate survey grid waypoints using Mission Planner's algorithm.
    
    Args:
        polygon_m: polygon vertices in meters [(x, y), ...]
        altitude: flight altitude in meters
        hfov, vfov: camera field of view in degrees
        lateral_overlap: side overlap percentage
        grid_angle: grid orientation in degrees (None = auto-detect)
        
    Returns: list of waypoints [(x, y, alt), ...]
    """
    print("\n" + "="*60)
    print("GENERATING SURVEY GRID")
    print("="*60)
    
    # Calculate line spacing
    spacing = calculate_line_spacing(altitude, hfov, lateral_overlap)
    print(f"Line spacing: {spacing:.2f} m")
    
    # Determine grid angle
    if grid_angle is None:
        grid_angle = get_longest_edge_angle(polygon_m)
        print(f"Auto-detected grid angle: {grid_angle:.1f}°")
    else:
        print(f"Using specified grid angle: {grid_angle:.1f}°")
    
    # Rotate polygon to align with grid (make grid lines horizontal)
    angle_rad = math.radians(grid_angle)
    cos_a = math.cos(-angle_rad)
    sin_a = math.sin(-angle_rad)
    
    rotated_polygon = []
    for x, y in polygon_m:
        x_rot = x * cos_a - y * sin_a
        y_rot = x * sin_a + y * cos_a
        rotated_polygon.append((x_rot, y_rot))
    
    # Get bounds of rotated polygon
    min_x, max_x, min_y, max_y = get_polygon_bounds(rotated_polygon)
    print(f"Rotated bounds: X=[{min_x:.1f}, {max_x:.1f}], Y=[{min_y:.1f}, {max_y:.1f}]")
    
    # Generate horizontal lines across the polygon
    # Extend lines beyond polygon bounds
    extension = max(max_x - min_x, max_y - min_y) * 0.5
    line_x_start = min_x - extension
    line_x_end = max_x + extension
    
    # Create lines at spacing intervals
    current_y = min_y
    lines = []
    line_num = 0
    
    while current_y <= max_y:
        lines.append({
            'start': (line_x_start, current_y),
            'end': (line_x_end, current_y),
            'y': current_y
        })
        current_y += spacing
        line_num += 1
    
    print(f"Generated {len(lines)} survey lines")
    
    # Clip lines to polygon and create waypoints
    waypoints_rotated = []
    
    for i, line in enumerate(lines):
        # Clip line to polygon
        intersections = clip_line_to_polygon(line['start'], line['end'], rotated_polygon)
        
        if len(intersections) >= 2:
            # Take first and last intersection points
            start_point = intersections[0]
            end_point = intersections[-1]
            
            # Lawnmower pattern: alternate direction
            if i % 2 == 0:
                waypoints_rotated.append(start_point)
                waypoints_rotated.append(end_point)
            else:
                waypoints_rotated.append(end_point)
                waypoints_rotated.append(start_point)
    
    print(f"Generated {len(waypoints_rotated)} waypoints (rotated)")
    
    # Rotate waypoints back to original orientation
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    
    waypoints_final = []
    for x_rot, y_rot in waypoints_rotated:
        x = x_rot * cos_a - y_rot * sin_a
        y = x_rot * sin_a + y_rot * cos_a
        waypoints_final.append((x, y, altitude))
    
    print(f"Final waypoints: {len(waypoints_final)}")
    print("="*60 + "\n")
    
    return waypoints_final


# ============================================================================
# MISSION STATISTICS
# ============================================================================
def calculate_mission_stats(waypoints, speed, forward_overlap, altitude, vfov):
    """Calculate mission statistics."""
    if len(waypoints) < 2:
        return {}
    
    # Calculate total distance
    total_distance = 0
    for i in range(len(waypoints) - 1):
        x1, y1, _ = waypoints[i]
        x2, y2, _ = waypoints[i + 1]
        distance = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        total_distance += distance
    
    # Calculate flight time
    flight_time = total_distance / speed  # seconds
    
    # Calculate number of photos
    photo_distance = calculate_photo_distance(altitude, vfov, forward_overlap)
    num_photos = int(total_distance / photo_distance) if photo_distance > 0 else 0
    
    # Calculate polygon area (approximate)
    # Using shoelace formula on first/last polygon
    
    return {
        'total_distance': total_distance,
        'flight_time': flight_time,
        'num_photos': num_photos,
        'num_waypoints': len(waypoints)
    }


# ============================================================================
# FILE OUTPUT
# ============================================================================
def save_waypoints_file(waypoints, ref_lat, ref_lon, filename="mission.waypoints"):
    """
    Save waypoints in Mission Planner .waypoints format.
    
    Format: QGC WPL 110
    0   1   0   16  0   0   0   0   lat lon alt 1
    """
    with open(filename, 'w') as f:
        f.write("QGC WPL 110\n")
        
        for i, (x, y, alt) in enumerate(waypoints):
            # Convert meters to lat/lon
            lat, lon = meters_to_latlon(x, y, ref_lat, ref_lon)
            
            # Waypoint format:
            # index current_wp coord_frame command p1 p2 p3 p4 lat lon alt autocontinue
            if i == 0:
                # First waypoint: MAV_CMD_NAV_TAKEOFF (22) or WAYPOINT (16)
                f.write(f"{i}\t1\t0\t16\t0\t0\t0\t0\t{lat:.8f}\t{lon:.8f}\t{alt:.2f}\t1\n")
            else:
                f.write(f"{i}\t0\t0\t16\t0\t0\t0\t0\t{lat:.8f}\t{lon:.8f}\t{alt:.2f}\t1\n")
    
    print(f"\n✓ Waypoints saved to: {filename}")


def save_simple_txt(waypoints, ref_lat, ref_lon, stats, filename="mission.txt"):
    """Save waypoints as simple text file with mission info."""
    with open(filename, 'w') as f:
        f.write(f"Mission Plan - Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*60 + "\n\n")
        
        f.write("PARAMETERS:\n")
        for key, value in MISSION_PARAMS.items():
            f.write(f"  {key}: {value}\n")
        f.write("\n")
        
        f.write("STATISTICS:\n")
        f.write(f"  Total Distance: {stats.get('total_distance', 0):.1f} m\n")
        f.write(f"  Flight Time: {stats.get('flight_time', 0)/60:.1f} min\n")
        f.write(f"  Estimated Photos: {stats.get('num_photos', 0)}\n")
        f.write(f"  Waypoints: {stats.get('num_waypoints', 0)}\n")
        f.write("\n")
        
        f.write("WAYPOINTS (Lat, Lon, Alt):\n")
        for i, (x, y, alt) in enumerate(waypoints):
            lat, lon = meters_to_latlon(x, y, ref_lat, ref_lon)
            f.write(f"  {i+1}: {lat:.8f}, {lon:.8f}, {alt:.2f}\n")
    
    print(f"✓ Mission details saved to: {filename}")


# ============================================================================
# MATPLOTLIB EVENT HANDLERS
# ============================================================================
def on_click(event):
    """Handle mouse click events for polygon drawing."""
    global polygon_points, polygon_patch, line, polygon_closed, waypoints
    
    if event.inaxes != ax:
        return
    
    # Regular polygon drawing (left click)
    if event.button == 1 and not polygon_closed:  # Left click
        polygon_points.append((event.xdata, event.ydata))
        
        # Update display
        if len(polygon_points) == 1:
            # First point
            line, = ax.plot([event.xdata], [event.ydata], 'ro-', linewidth=2, markersize=6)
        else:
            # Update line
            xs, ys = zip(*polygon_points)
            line.set_data(xs, ys)
        
        plt.draw()
        print(f"Point {len(polygon_points)}: ({event.xdata:.2f}, {event.ydata:.2f})")
    
    # Right click - close polygon
    elif event.button == 3 and not polygon_closed and len(polygon_points) >= 3:
        close_polygon()


def on_key(event):
    """Handle keyboard events."""
    global polygon_closed
    
    if event.key == 'enter' and not polygon_closed and len(polygon_points) >= 3:
        close_polygon()


def close_polygon():
    """Close the polygon and generate mission automatically."""
    global polygon_closed, polygon_patch, line
    
    polygon_closed = True
    print(f"\n✓ Polygon closed with {len(polygon_points)} vertices")
    
    # Draw filled polygon
    if polygon_patch:
        polygon_patch.remove()
    
    polygon_patch = MplPolygon(polygon_points, alpha=0.3, facecolor='lightblue', 
                              edgecolor='blue', linewidth=2)
    ax.add_patch(polygon_patch)
    
    # Remove the line
    if line:
        line.remove()
    
    # Draw vertices
    xs, ys = zip(*polygon_points)
    ax.plot(xs, ys, 'bo', markersize=8)
    
    plt.draw()
    
    # Automatically generate the flight path
    print(f"\nUsing reference coordinates: {reference_lat:.6f}, {reference_lon:.6f}")
    generate_and_display_mission()


def generate_and_display_mission():
    """Generate flight path and display it."""
    global waypoints
    
    # Convert polygon points to meters (using simple scaling for now)
    # In real application, first point would be at reference lat/lon
    polygon_m = []
    
    # Use first polygon point as local origin (0, 0)
    origin_x, origin_y = polygon_points[0]
    
    # Simple scaling: 100 canvas units = 100 meters (adjust as needed)
    scale = 1.0  # 1:1 mapping for now
    
    for px, py in polygon_points:
        x_m = (px - origin_x) * scale
        y_m = (py - origin_y) * scale
        polygon_m.append((x_m, y_m))
    
    print(f"\nPolygon in meters (relative to first point):")
    for i, (x, y) in enumerate(polygon_m):
        print(f"  Point {i+1}: ({x:.2f}, {y:.2f})")
    
    # Generate survey grid
    waypoints = generate_survey_grid(
        polygon_m,
        MISSION_PARAMS['altitude'],
        MISSION_PARAMS['camera_hfov'],
        MISSION_PARAMS['camera_vfov'],
        MISSION_PARAMS['lateral_overlap'],
        MISSION_PARAMS['grid_angle']
    )
    
    # Convert waypoints back to canvas coordinates for display
    waypoints_canvas = []
    for x_m, y_m, alt in waypoints:
        px = (x_m / scale) + origin_x
        py = (y_m / scale) + origin_y
        waypoints_canvas.append((px, py))
    
    # Plot flight path
    if len(waypoints_canvas) > 0:
        # Draw path lines
        xs, ys = zip(*waypoints_canvas)
        ax.plot(xs, ys, 'r-', linewidth=1.5, alpha=0.7, label='Flight Path')
        ax.plot(xs, ys, 'ro', markersize=4)
        
        # Number waypoints
        for i, (x, y) in enumerate(waypoints_canvas):
            if i % 2 == 0:  # Label every other waypoint to avoid clutter
                ax.annotate(str(i+1), (x, y), fontsize=8, ha='right')
        
        ax.legend()
        plt.draw()
    
    # Calculate and display statistics
    stats = calculate_mission_stats(
        waypoints,
        MISSION_PARAMS['aircraft_speed'],
        MISSION_PARAMS['forward_overlap'],
        MISSION_PARAMS['altitude'],
        MISSION_PARAMS['camera_vfov']
    )
    
    print("\n" + "="*60)
    print("MISSION STATISTICS")
    print("="*60)
    print(f"Total Distance: {stats['total_distance']:.1f} m ({stats['total_distance']/1000:.2f} km)")
    print(f"Flight Time: {stats['flight_time']/60:.1f} minutes")
    print(f"Estimated Photos: {stats['num_photos']}")
    print(f"Number of Waypoints: {stats['num_waypoints']}")
    
    # Calculate GSD
    gsd = calculate_gsd(MISSION_PARAMS['altitude'], MISSION_PARAMS['camera_hfov'], 
                       MISSION_PARAMS['camera_width'])
    print(f"Ground Sampling Distance: {gsd:.2f} cm/pixel")
    print("="*60 + "\n")
    
    # Save files
    # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # save_waypoints_file(waypoints, reference_lat, reference_lon, 
    #                    f"mission_{timestamp}.waypoints")
    # save_simple_txt(waypoints, reference_lat, reference_lon, stats,
    #                f"mission_{timestamp}.txt")
    
    print("\n✓ Mission generation complete!")
    print("Close the window to exit.")


# ============================================================================
# MAIN PROGRAM
# ============================================================================
def main():
    """Main program entry point."""
    global fig, ax
    
    print("\n" + "="*60)
    print("MISSION PLANNER DEVELOPMENT TOOL")
    print("Survey Grid Generator")
    print("="*60)
    print("\nMISSION PARAMETERS:")
    for key, value in MISSION_PARAMS.items():
        print(f"  {key}: {value}")
    print("\n" + "="*60)
    print("INSTRUCTIONS:")
    print("  1. LEFT-CLICK to add polygon vertices")
    print("  2. Press ENTER or RIGHT-CLICK to close polygon")
    print("  3. Flight path will be generated automatically")
    print(f"\nReference Origin: {reference_lat:.6f}, {reference_lon:.6f}")
    print("  (Edit reference_lat/reference_lon in script to change)")
    print("="*60 + "\n")
    
    # Create interactive plot
    fig, ax = plt.subplots(figsize=(12, 10))
    ax.set_xlim(0, 500)
    ax.set_ylim(0, 500)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    ax.set_title('Survey Mission Planner - Draw Polygon', fontsize=14, fontweight='bold')
    ax.set_xlabel('X (canvas units)', fontsize=10)
    ax.set_ylabel('Y (canvas units)', fontsize=10)
    
    # Connect event handlers
    fig.canvas.mpl_connect('button_press_event', on_click)
    fig.canvas.mpl_connect('key_press_event', on_key)
    
    plt.tight_layout()
    plt.show()
    
    print("\n" + "="*60)
    print("Program ended.")
    print("="*60)


if __name__ == "__main__":
    main()
